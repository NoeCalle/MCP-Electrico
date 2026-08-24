"""Genera el reporte reproducible de benchmarks P1 en JSON."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp_electrico.benchmarks import run_p1_benchmarks


if __name__ == "__main__":
    report = run_p1_benchmarks()
    target = Path("benchmark_p1.json")
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False))
    if not report["summary"]["pass"]:
        raise SystemExit(1)
