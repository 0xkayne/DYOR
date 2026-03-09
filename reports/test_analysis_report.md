# DYOR Test Analysis Report

**Generated**: 2026-03-09T23:40:05.524699

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | 496 |
| Passed | 496 |
| Failed | 0 |
| Skipped | 0 |
| Errors | 0 |
| Overall Coverage | 72.9% |

## Per-Module Test Results

| Module | Total | Passed | Failed | Skipped |
|--------|-------|--------|--------|---------|
| test_agents | 85 | 85 | 0 | 0 |
| test_api | 70 | 70 | 0 | 0 |
| test_eval | 122 | 122 | 0 | 0 |
| test_graph | 17 | 17 | 0 | 0 |
| test_guardrails | 23 | 23 | 0 | 0 |
| test_mcp | 97 | 97 | 0 | 0 |
| test_memory | 10 | 10 | 0 | 0 |
| test_rag | 50 | 50 | 0 | 0 |
| test_schemas | 22 | 22 | 0 | 0 |

## Coverage by Module

| Module | Statements | Missing | Coverage |
|--------|-----------|---------|----------|
| api/__init__.py | 2 | 0 | 100.0% |
| api/main.py | 40 | 18 | 55.0% |
| api/middleware | 63 | 11 | 82.5% |
| api/routes | 280 | 101 | 63.9% |
| eval/__init__.py | 0 | 0 | 0% |
| eval/metrics.py | 116 | 6 | 94.8% |
| eval/run_eval.py | 154 | 14 | 90.9% |
| src/__init__.py | 0 | 0 | 0% |
| src/agents | 632 | 174 | 72.5% |
| src/config.py | 25 | 0 | 100.0% |
| src/graph | 141 | 7 | 95.0% |
| src/guardrails | 86 | 7 | 91.9% |
| src/mcp_servers | 424 | 75 | 82.3% |
| src/memory | 70 | 6 | 91.4% |
| src/rag | 755 | 358 | 52.6% |
| src/schemas | 76 | 0 | 100.0% |

## Risk Assessment

| Module | Coverage | Risk Level |
|--------|----------|------------|
| api/__init__.py | 100.0% | Low |
| api/main.py | 55.0% | High |
| api/middleware | 82.5% | Low |
| api/routes | 63.9% | Medium |
| eval/__init__.py | 0.0% | Critical |
| eval/metrics.py | 94.8% | Low |
| eval/run_eval.py | 90.9% | Low |
| src/__init__.py | 0.0% | Critical |
| src/agents | 72.5% | Medium |
| src/config.py | 100.0% | Low |
| src/graph | 95.0% | Low |
| src/guardrails | 91.9% | Low |
| src/mcp_servers | 82.3% | Low |
| src/memory | 91.4% | Low |
| src/rag | 52.6% | High |
| src/schemas | 100.0% | Low |

## Overall Status: **PASS**

- All tests passing: Yes
- No skipped tests: Yes
- Coverage target (>70%): Yes
