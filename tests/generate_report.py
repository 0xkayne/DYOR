"""Generate a structured test analysis report from pytest and coverage output.

Parses pytest results and coverage data to produce a Markdown report
with per-module statistics and risk assessment.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPORTS_DIR = Path(__file__).parent.parent / "reports"


def _run_pytest() -> tuple[str, int]:
    """Run pytest with coverage and capture output.

    Returns:
        Tuple of (stdout text, return code).
    """
    cmd = [
        sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short",
        "--cov=src", "--cov=api", "--cov=eval",
        "--cov-report=term-missing",
        "--cov-report=json:reports/coverage.json",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent)
    return result.stdout + result.stderr, result.returncode


def _parse_test_results(output: str) -> dict:
    """Parse pytest verbose output for test counts.

    Args:
        output: Raw pytest stdout/stderr.

    Returns:
        Dict with total, passed, failed, skipped, errors counts and per-module breakdown.
    """
    # Parse summary line like "496 passed in 50.92s" or "1 failed, 495 passed"
    summary = {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 0}
    for key in ("passed", "failed", "skipped", "error"):
        m = re.search(rf"(\d+) {key}", output)
        if m:
            mapped_key = "errors" if key == "error" else key
            summary[mapped_key] = int(m.group(1))
    summary["total"] = summary["passed"] + summary["failed"] + summary["skipped"] + summary["errors"]

    # Per-module breakdown
    modules: dict[str, dict[str, int]] = {}
    for match in re.finditer(r"(tests/\S+)::(\S+) (PASSED|FAILED|SKIPPED|ERROR)", output):
        module_path = match.group(1)
        # Group by test directory
        parts = module_path.split("/")
        if len(parts) >= 2:
            module = parts[1]  # e.g., "test_agents"
        else:
            module = parts[0]
        if module not in modules:
            modules[module] = {"passed": 0, "failed": 0, "skipped": 0, "error": 0, "total": 0}
        status = match.group(3).lower()
        if status in modules[module]:
            modules[module][status] += 1
        modules[module]["total"] += 1

    return {"summary": summary, "modules": modules}


def _parse_coverage(coverage_path: Path) -> dict:
    """Parse coverage JSON report.

    Args:
        coverage_path: Path to coverage.json.

    Returns:
        Dict with per-file and overall coverage data.
    """
    if not coverage_path.exists():
        return {"overall": 0, "files": {}}

    data = json.loads(coverage_path.read_text(encoding="utf-8"))
    totals = data.get("totals", {})
    overall = totals.get("percent_covered", 0)

    files = {}
    for filepath, file_data in data.get("files", {}).items():
        summary = file_data.get("summary", {})
        files[filepath] = {
            "statements": summary.get("num_statements", 0),
            "missing": summary.get("missing_lines", 0),
            "coverage": summary.get("percent_covered", 0),
            "missing_lines": file_data.get("missing_lines", []),
        }

    return {"overall": round(overall, 1), "files": files}


def _generate_markdown(test_results: dict, coverage: dict) -> str:
    """Generate the Markdown analysis report.

    Args:
        test_results: Parsed test results.
        coverage: Parsed coverage data.

    Returns:
        Markdown string.
    """
    s = test_results["summary"]
    lines = [
        "# DYOR Test Analysis Report",
        f"\n**Generated**: {datetime.now().isoformat()}",
        f"\n## Summary",
        f"\n| Metric | Value |",
        f"|--------|-------|",
        f"| Total Tests | {s['total']} |",
        f"| Passed | {s['passed']} |",
        f"| Failed | {s['failed']} |",
        f"| Skipped | {s['skipped']} |",
        f"| Errors | {s['errors']} |",
        f"| Overall Coverage | {coverage['overall']}% |",
        f"\n## Per-Module Test Results",
        f"\n| Module | Total | Passed | Failed | Skipped |",
        f"|--------|-------|--------|--------|---------|",
    ]

    for module, counts in sorted(test_results["modules"].items()):
        lines.append(
            f"| {module} | {counts['total']} | {counts['passed']} "
            f"| {counts['failed']} | {counts['skipped']} |"
        )

    # Coverage by module group
    lines.extend([
        f"\n## Coverage by Module",
        f"\n| Module | Statements | Missing | Coverage |",
        f"|--------|-----------|---------|----------|",
    ])

    module_groups: dict[str, dict] = {}
    for filepath, data in coverage.get("files", {}).items():
        parts = filepath.split("/")
        if len(parts) >= 2:
            group = f"{parts[0]}/{parts[1]}"
        else:
            group = parts[0]
        if group not in module_groups:
            module_groups[group] = {"statements": 0, "missing": 0}
        module_groups[group]["statements"] += data["statements"]
        module_groups[group]["missing"] += data["missing"]

    for group, data in sorted(module_groups.items()):
        cov = round(
            ((data["statements"] - data["missing"]) / data["statements"] * 100)
            if data["statements"] > 0 else 0, 1
        )
        lines.append(f"| {group} | {data['statements']} | {data['missing']} | {cov}% |")

    # Risk assessment
    lines.extend([
        f"\n## Risk Assessment",
        f"\n| Module | Coverage | Risk Level |",
        f"|--------|----------|------------|",
    ])
    for group, data in sorted(module_groups.items()):
        cov = ((data["statements"] - data["missing"]) / data["statements"] * 100) if data["statements"] > 0 else 0
        if cov >= 80:
            risk = "Low"
        elif cov >= 60:
            risk = "Medium"
        elif cov >= 40:
            risk = "High"
        else:
            risk = "Critical"
        lines.append(f"| {group} | {cov:.1f}% | {risk} |")

    # Status
    status = "PASS" if s["failed"] == 0 and s["skipped"] == 0 and s["errors"] == 0 else "FAIL"
    lines.extend([
        f"\n## Overall Status: **{status}**",
        f"\n- All tests passing: {'Yes' if s['failed'] == 0 else 'No'}",
        f"- No skipped tests: {'Yes' if s['skipped'] == 0 else 'No'}",
        f"- Coverage target (>70%): {'Yes' if coverage['overall'] >= 70 else 'No'}",
    ])

    return "\n".join(lines) + "\n"


def main() -> None:
    """Run tests, parse results, and generate the analysis report."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    print("Running pytest with coverage...")
    output, returncode = _run_pytest()

    print("Parsing test results...")
    test_results = _parse_test_results(output)

    print("Parsing coverage data...")
    coverage = _parse_coverage(REPORTS_DIR / "coverage.json")

    print("Generating report...")
    report_md = _generate_markdown(test_results, coverage)

    report_path = REPORTS_DIR / "test_analysis_report.md"
    report_path.write_text(report_md, encoding="utf-8")
    print(f"Report saved to: {report_path}")

    # Also save raw JSON data
    json_path = REPORTS_DIR / "test_analysis_data.json"
    json_path.write_text(
        json.dumps({"tests": test_results, "coverage": coverage}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"JSON data saved to: {json_path}")


if __name__ == "__main__":
    main()
