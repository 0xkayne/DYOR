"""Disclaimer injection to ensure all outputs include proper legal disclaimers.

Provides a standard risk disclaimer and a helper to inject it into
analysis reports that may be missing one.
"""

import structlog

logger = structlog.get_logger(__name__)

RISK_DISCLAIMER: str = (
    "本分析报告仅供参考，不构成任何投资建议。加密货币市场波动剧烈，"
    "投资存在高风险，包括但不限于价格大幅波动、流动性风险、监管政策变化、"
    "技术安全风险及项目失败风险。过往表现不代表未来收益。"
    "请在充分了解相关风险后，根据自身财务状况和风险承受能力做出独立判断。"
    "投资者应自行承担所有投资决策的后果。DYOR (Do Your Own Research)。"
)


def inject_disclaimer(report: dict) -> dict:
    """Ensure the report contains a proper disclaimer in investment_recommendation.

    If the disclaimer field is missing or empty, injects the standard
    RISK_DISCLAIMER. Does not overwrite an existing non-empty disclaimer.

    Args:
        report: The analysis report dict. Modified in-place and returned.

    Returns:
        The report dict with disclaimer guaranteed to be present.
    """
    if not isinstance(report, dict):
        logger.warning("inject_disclaimer_skipped", reason="report is not a dict")
        return report

    rec = report.get("investment_recommendation")
    if rec is None:
        # Create a minimal investment_recommendation with disclaimer
        report["investment_recommendation"] = {"disclaimer": RISK_DISCLAIMER}
        logger.info("disclaimer_injected", target="new_investment_recommendation")
        return report

    if not isinstance(rec, dict):
        logger.warning("inject_disclaimer_skipped", reason="investment_recommendation is not a dict")
        return report

    existing = rec.get("disclaimer")
    if not existing or not isinstance(existing, str) or len(existing.strip()) == 0:
        rec["disclaimer"] = RISK_DISCLAIMER
        logger.info("disclaimer_injected", target="existing_investment_recommendation")
    else:
        logger.debug("disclaimer_already_present")

    return report
