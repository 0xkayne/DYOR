"""Output validation logic to ensure agent outputs meet quality standards.

Validates analyst output against the AnalysisReport schema requirements,
checks for forbidden patterns, and enforces compliance rules.
"""

import re

import structlog

logger = structlog.get_logger(__name__)

# Forbidden absolute expressions in Chinese and English
FORBIDDEN_PATTERNS: list[str] = [
    "一定",
    "必须",
    "保证",
    "肯定会",
    "绝对",
    "guaranteed",
    "definitely",
    "certainly",
    "risk-free",
    "risk free",
]


def validate_output(report: dict) -> tuple[bool, list[str]]:
    """Validate an analyst report for completeness and compliance.

    Checks:
    - All required top-level fields exist.
    - Forbidden absolute language is absent.
    - Confidence is <= 0.8.
    - Disclaimer is present and non-empty.
    - Sources list is non-empty.

    Args:
        report: The analysis report dict to validate.

    Returns:
        A tuple of (is_valid, issues) where is_valid is True if
        no issues were found, and issues is a list of human-readable
        problem descriptions.
    """
    issues: list[str] = []

    if not isinstance(report, dict):
        return False, ["Report is not a valid dictionary"]

    # --- Required top-level fields ---
    required_fields = [
        "project_name",
        "analysis_date",
        "fundamental_analysis",
        "investment_recommendation",
    ]
    for field in required_fields:
        if field not in report or report[field] is None:
            issues.append(f"Missing required field: {field}")

    # --- Fundamental analysis checks ---
    fa = report.get("fundamental_analysis")
    if isinstance(fa, dict):
        score_fields = ["team_score", "product_score", "track_score", "tokenomics_score"]
        for sf in score_fields:
            val = fa.get(sf)
            if val is None:
                issues.append(f"Missing fundamental_analysis.{sf}")
            elif not isinstance(val, (int, float)) or val < 1 or val > 10:
                issues.append(
                    f"fundamental_analysis.{sf} must be between 1 and 10, got {val}"
                )

        sources = fa.get("sources")
        if not sources or not isinstance(sources, list) or len(sources) == 0:
            issues.append("fundamental_analysis.sources must be a non-empty list")

    # --- Investment recommendation checks ---
    rec = report.get("investment_recommendation")
    if isinstance(rec, dict):
        # Confidence cap
        confidence = rec.get("confidence")
        if confidence is not None and isinstance(confidence, (int, float)):
            if confidence > 0.8:
                issues.append(
                    f"Confidence must be <= 0.8, got {confidence}"
                )

        # Disclaimer
        disclaimer = rec.get("disclaimer")
        if not disclaimer or not isinstance(disclaimer, str) or len(disclaimer.strip()) == 0:
            issues.append("investment_recommendation.disclaimer must be a non-empty string")

        # Key reasons and risk factors
        key_reasons = rec.get("key_reasons")
        if not key_reasons or not isinstance(key_reasons, list) or len(key_reasons) < 1:
            issues.append("investment_recommendation.key_reasons must be a non-empty list")

        risk_factors = rec.get("risk_factors")
        if not risk_factors or not isinstance(risk_factors, list) or len(risk_factors) < 1:
            issues.append("investment_recommendation.risk_factors must be a non-empty list")

        # Rating validity
        valid_ratings = {"strong_buy", "buy", "hold", "sell", "strong_sell"}
        rating = rec.get("rating")
        if rating and rating not in valid_ratings:
            issues.append(f"Invalid rating: {rating}. Must be one of {valid_ratings}")

    # --- Forbidden patterns check (scan full report text) ---
    report_text = _extract_text(report)
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(re.escape(pattern), report_text, re.IGNORECASE):
            issues.append(f"Forbidden absolute expression found: '{pattern}'")

    is_valid = len(issues) == 0
    if not is_valid:
        logger.warning("output_validation_failed", issue_count=len(issues), issues=issues)
    else:
        logger.info("output_validation_passed")

    return is_valid, issues


def _extract_text(obj: object, depth: int = 0) -> str:
    """Recursively extract all string values from a nested dict/list structure.

    Args:
        obj: The object to extract text from.
        depth: Current recursion depth (safety limit at 10).

    Returns:
        Concatenated string of all text values found.
    """
    if depth > 10:
        return ""
    if isinstance(obj, str):
        return obj + " "
    if isinstance(obj, dict):
        return " ".join(_extract_text(v, depth + 1) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return " ".join(_extract_text(item, depth + 1) for item in obj)
    return ""
