from __future__ import annotations
import time
from typing import Any, Dict, List
import httpx
from bitnet_runtime.plugins.vertical_registry import VerticalManifest
from bitnet_runtime.logging import logger
from ..base_vertical import BaseVertical
from .reporter import QAReporter, QATestResult

class QABoxRunner(BaseVertical):
    manifest = VerticalManifest(
        name="qa",
        title="AI QA Box",
        description="Autonomous Web Crawler & Regression Checker",
    )
    """
    AI QA Box:
    - Continuous automated testing and website/API verification
    - Broken link & HTTP error detection
    - Automated markdown report generation
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.reporter = QAReporter()

    async def initialize(self) -> None:
        logger.info("AI QA Box runner initialized.")

    async def run_endpoint_checks(self, urls: List[str]) -> Dict[str, Any]:
        results: List[QATestResult] = []
        async with httpx.AsyncClient(timeout=10.0) as client:
            for url in urls:
                start = time.perf_counter()
                errors = []
                status_code = 0
                passed = False
                try:
                    res = await client.get(url)
                    status_code = res.status_code
                    passed = (200 <= status_code < 400)
                    if not passed:
                        errors.append(f"HTTP Status {status_code}")
                except Exception as e:
                    errors.append(str(e))

                duration = (time.perf_counter() - start) * 1000
                results.append(
                    QATestResult(
                        test_name=f"Endpoint Check: {url}",
                        target_url=url,
                        passed=passed,
                        status_code=status_code,
                        duration_ms=duration,
                        errors=errors,
                    )
                )

        report_md = self.reporter.format_markdown_report(results)
        return {
            "results": results,
            "report_markdown": report_md,
            "all_passed": all(r.passed for r in results),
        }
