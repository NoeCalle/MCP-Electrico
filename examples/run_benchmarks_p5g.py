"""Genera el reporte reproducible de benchmarks P5G."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp_electrico import p5_benchmarks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="benchmark_p5g.json")
    args = parser.parse_args()

    report = p5_benchmarks.ejecutar_benchmarks_p5g()
    path = Path(args.output)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if not report.get("pass"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
