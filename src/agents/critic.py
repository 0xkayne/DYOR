"""Critic agent that reviews analysis quality and requests revisions if needed.

Validates analysis reports for completeness, compliance, consistency,
and citation quality. Uses the Opus model for high-quality judgment.
"""

from __future__ import annotations

import asyncio
import json
import re

import structlog
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.prompts.critic_prompt import CRITIC_SYSTEM_PROMPT
from src.config import settings
from src.graph.state import AgentState
from src.guardrails.output_validator import validate_output

logger = structlog.get_logger(__name__)

# Patterns that indicate absolute investment claims (forbidden)
_FORBIDDEN_PATTERNS: list[str] = [
    r"guaranteed\s+returns?",
    r"risk[\-\s]?free",
    r"certain(ly)?\s+(will|to)\s+(rise|increase|profit)",
    r"definitely\s+(buy|invest|profitable)",
    r"100%\s+(safe|certain|guaranteed)",
    r"cannot\s+lose",
    r"保证.*收益",
    r"稳赚",
    r"一定.*涨",
    r"绝对.*赚",
    r"零风险",
    r"不可能.*亏",
]


def _check_forbidden_patterns(text: str) -> list[dict]:
    """Check text for forbidden absolute investment claim patterns.

    Args:
        text: Text to scan.

    Returns:
        List of issue dicts for each pattern found.
    """
    issues = []
    text_lower = text.lower()
    for pattern in _FORBIDDEN_PATTERNS:
        if re.search(pattern, text_lower):
            issues.append({
                "category": "compliance",
                "severity": "critical",
                "description": f"Forbidden pattern detected: '{pattern}'",
            })
    return issues


def _check_required_fields(report: dict) -> list[dict]:
    """Validate that all required fields are present in the report.

    Args:
        report: The analysis report dict.

    Returns:
        List of issue dicts for missing fields.
    """
    issues = []

    if not report.get("project_name"):
        issues.append({
            "category": "completeness",
            "severity": "critical",
            "description": "Missing required field: project_name",
        })

    workflow_type = report.get("workflow_type")
    if workflow_type not in {"deep_dive", "compare", "brief", "qa"}:
        issues.append({
            "category": "completeness",
            "severity": "critical",
            "description": f"Invalid workflow_type: {workflow_type}",
        })

    # Check fundamental_analysis
    fa = report.get("fundamental_analysis")
    if fa is not None:
        if not fa.get("summary"):
            issues.append({
                "category": "completeness",
                "severity": "warning",
                "description": "fundamental_analysis.summary is empty",
            })
        for score_field in ["team_score", "product_score", "track_score", "tokenomics_score"]:
            score = fa.get(score_field)
            if score is not None and not (1.0 <= float(score) <= 10.0):
                issues.append({
                    "category": "consistency",
                    "severity": "critical",
                    "description": f"{score_field} out of range (1-10): {score}",
                })

    # Check investment_recommendation
    rec = report.get("investment_recommendation")
    if rec is None:
        issues.append({
            "category": "completeness",
            "severity": "critical",
            "description": "Missing investment_recommendation section",
        })
    else:
        if rec.get("rating") not in {"strong_buy", "buy", "hold", "sell", "strong_sell"}:
            issues.append({
                "category": "completeness",
                "severity": "critical",
                "description": f"Invalid rating: {rec.get('rating')}",
            })
        if not rec.get("disclaimer"):
            issues.append({
                "category": "compliance",
                "severity": "critical",
                "description": "Missing disclaimer in investment_recommendation",
            })
        if not rec.get("key_reasons"):
            issues.append({
                "category": "completeness",
                "severity": "warning",
                "description": "No key_reasons provided",
            })
        if not rec.get("risk_factors"):
            issues.append({
                "category": "completeness",
                "severity": "warning",
                "description": "No risk_factors provided",
            })

    return issues


class CriticAgent:
    """Reviews analysis reports for quality and compliance.

    Uses the Opus model for nuanced quality judgment and also runs
    programmatic guardrail checks for forbidden patterns and required fields.
    """

    def __init__(self) -> None:
        """Initialize the CriticAgent with a ChatAnthropic LLM."""
        self._llm = ChatAnthropic(
            model=settings.llm_model_opus,
            api_key=settings.anthropic_api_key,
            temperature=settings.llm_temperature,
            max_tokens=2048,
        )

    async def invoke(self, report: dict) -> dict:
        """Review an analysis report and decide whether to approve or reject.

        Args:
            report: The analysis report dict to review.

        Returns:
            Dict with keys:
                - approved: bool indicating pass/fail
                - feedback: detailed feedback string
                - issues: list of issue dicts
        """
        try:
            result = await asyncio.wait_for(
                self._review(report),
                timeout=settings.agent_timeout * 2,
            )
            return result
        except asyncio.TimeoutError:
            logger.error("critic_timeout")
            # On timeout, auto-approve to prevent blocking
            return {
                "approved": True,
                "feedback": "Critic review timed out. Auto-approved with caution.",
                "issues": [{
                    "category": "quality",
                    "severity": "warning",
                    "description": "Critic review could not complete within timeout",
                }],
            }
        except Exception as exc:
            logger.error("critic_error", error=str(exc))
            return {
                "approved": True,
                "feedback": f"Critic review failed: {exc}. Auto-approved with caution.",
                "issues": [{
                    "category": "quality",
                    "severity": "warning",
                    "description": f"Critic error: {exc}",
                }],
            }

    async def _review(self, report: dict) -> dict:
        """Run programmatic checks and LLM review on the report.

        Args:
            report: The analysis report dict.

        Returns:
            Review result dict.
        """
        all_issues: list[dict] = []

        # Step 1: Programmatic guardrail checks
        report_text = json.dumps(report, ensure_ascii=False, default=str)
        all_issues.extend(_check_forbidden_patterns(report_text))
        all_issues.extend(_check_required_fields(report))

        # If there are already critical programmatic issues, reject without LLM
        critical_programmatic = [i for i in all_issues if i["severity"] == "critical"]
        if critical_programmatic:
            feedback = "Report rejected due to programmatic validation failures:\n"
            for issue in critical_programmatic:
                feedback += f"- [{issue['category']}] {issue['description']}\n"

            logger.info(
                "critic_rejected_programmatic",
                critical_count=len(critical_programmatic),
            )

            return {
                "approved": False,
                "feedback": feedback,
                "issues": all_issues,
            }

        # Step 2: LLM-based quality review
        llm_result = await self._llm_review(report_text)
        if llm_result:
            llm_issues = llm_result.get("issues", [])
            all_issues.extend(llm_issues)

            # Use LLM's approval decision, but override if guardrails found issues
            llm_approved = llm_result.get("approved", True)
            llm_feedback = llm_result.get("feedback", "")
        else:
            llm_approved = True
            llm_feedback = "LLM review unavailable."

        # Final decision
        critical_count = sum(1 for i in all_issues if i.get("severity") == "critical")
        warning_count = sum(1 for i in all_issues if i.get("severity") == "warning")

        if critical_count > 0:
            approved = False
        elif warning_count >= 3:
            approved = False
        else:
            approved = llm_approved

        logger.info(
            "critic_result",
            approved=approved,
            critical_issues=critical_count,
            warning_issues=warning_count,
        )

        return {
            "approved": approved,
            "feedback": llm_feedback,
            "issues": all_issues,
        }

    async def _llm_review(self, report_text: str) -> dict | None:
        """Call the LLM for qualitative review of the report.

        Args:
            report_text: JSON string of the report.

        Returns:
            Parsed review dict, or None on failure.
        """
        try:
            messages = [
                SystemMessage(content=CRITIC_SYSTEM_PROMPT),
                HumanMessage(content=f"Review this analysis report:\n\n{report_text}"),
            ]
            response = await self._llm.ainvoke(messages)
            raw = response.content
            if isinstance(raw, list):
                raw = raw[0].get("text", "") if raw else ""

            # Extract JSON
            json_str = raw
            if "```json" in raw:
                start = raw.index("```json") + 7
                end = raw.index("```", start)
                json_str = raw[start:end].strip()
            elif "```" in raw:
                start = raw.index("```") + 3
                end = raw.index("```", start)
                json_str = raw[start:end].strip()
            else:
                first_brace = raw.find("{")
                last_brace = raw.rfind("}")
                if first_brace != -1 and last_brace != -1:
                    json_str = raw[first_brace:last_brace + 1]

            return json.loads(json_str)
        except Exception as exc:
            logger.warning("critic_llm_review_failed", error=str(exc))
            return None


_critic = CriticAgent()


async def critic_node(state: AgentState) -> dict:
    """LangGraph node function wrapping the CriticAgent.

    Enforces max revision_count to prevent infinite loops. If
    revision_count >= max_revision_count, auto-approves the report.

    Args:
        state: Current agent state with analysis_report and revision_count.

    Returns:
        Dict with critic_approved, critic_feedback, and revision_count.
    """
    report = state.get("analysis_report")
    revision_count = state.get("revision_count", 0)

    # Guard: force approval if max revisions reached
    if revision_count >= settings.max_revision_count:
        logger.warning(
            "critic_max_revisions_reached",
            revision_count=revision_count,
            max=settings.max_revision_count,
        )
        return {
            "critic_approved": True,
            "critic_feedback": (
                f"Auto-approved after {revision_count} revision(s) "
                f"(max {settings.max_revision_count} reached)."
            ),
            "revision_count": revision_count,
        }

    if report is None:
        logger.warning("critic_no_report")
        return {
            "critic_approved": False,
            "critic_feedback": "No analysis report to review.",
            "revision_count": revision_count,
        }

    # Run programmatic guardrail validation first
    is_valid, guardrail_issues = validate_output(report)

    # Run the full critic review
    result = await _critic.invoke(report)

    approved = result.get("approved", False)
    feedback = result.get("feedback", "")

    # If guardrail validation failed, always reject (unless max revisions reached)
    if not is_valid:
        guardrail_msg = "Guardrail validation issues: " + "; ".join(guardrail_issues)
        if feedback:
            feedback = f"{guardrail_msg}\n\nLLM Critic feedback: {feedback}"
        else:
            feedback = guardrail_msg
        approved = False

    new_revision_count = revision_count
    if not approved:
        new_revision_count = revision_count + 1

    logger.info(
        "critic_node_result",
        approved=approved,
        revision_count=new_revision_count,
    )

    return {
        "critic_approved": approved,
        "critic_feedback": feedback,
        "revision_count": new_revision_count,
    }
