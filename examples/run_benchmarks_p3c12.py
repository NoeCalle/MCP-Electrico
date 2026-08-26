"""Genera el artefacto reproducible P3C12A de benchmarks primarios independientes."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp_electrico import ampacity_independent_benchmarks


OUTPUT = ROOT / "benchmark_p3c12.json"


def main() -> int:
    report = ampacity_independent_benchmarks.run_suite()
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "suite_id": report["suite_id"],
        "cases": report["cases"],
        "passed": report["passed"],
        "failed": report["failed"],
        "pass": report["pass"],
    }, ensure_ascii=False))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
