"""Genera el benchmark independiente P4C09A para el alcance 3F max/min.

Uso:
    python examples/benchmark_p4_3ph.py
    python examples/benchmark_p4_3ph.py --output benchmark_p4_3ph.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp_electrico import iec60909_benchmarks


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark independiente P4 3F")
    parser.add_argument("--output", default="benchmark_p4_3ph.json")
    args = parser.parse_args()

    result = iec60909_benchmarks.run_suite()
    target = Path(args.output).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "schema": result["schema"],
        "pass": result["pass"],
        "cases": len(result["cases"]),
        "output": str(target),
    }, ensure_ascii=False))
    if not result["pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
