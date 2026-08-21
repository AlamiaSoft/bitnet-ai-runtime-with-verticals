from __future__ import annotations
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List

@dataclass
class QATestResult:
    test_name: str
    target_url: str
    passed: bool
    status_code: int
    duration_ms: float
    errors: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

class QAReporter:
    def format_markdown_report(self, results: List[QATestResult]) -> str:
        passed_count = sum(1 for r in results if r.passed)
        total = len(results)

        lines = [
            "# ?? AI QA Box Test Report",
            f"**Total Checks**: {total} | **Passed**: {passed_count} | **Failed**: {total - passed_count}",
            "",
            "| Test Name | Target URL | Status | Duration | Errors |",
            "|---|---|---|---|---|",
        ]
        for r in results:
            status_badge = "? PASS" if r.passed else "? FAIL"
            err_msg = ", ".join(r.errors) if r.errors else "None"
            lines.append(f"| {r.test_name} | {r.target_url} | {status_badge} | {r.duration_ms:.1f}ms | {err_msg} |")

        return "\n".join(lines)
