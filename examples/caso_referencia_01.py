"""Ejecuta REF-01, el primer caso canónico numérico de MCP Eléctrico.

REF-01 usa una solución analítica independiente congelada como patrón oro y
compara contra OpenDSS con las tolerancias P1 publicadas.

Uso:
    python examples/caso_referencia_01.py
    python examples/caso_referencia_01.py --output resultado_ref01.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp_electrico import benchmarks


MANIFEST = ROOT / "mcp_electrico" / "data" / "reference_case_01.json"


def _load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _frozen_reference_consistency(
    calculated: dict[str, float], frozen: dict[str, float]
) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for name, expected in frozen.items():
        actual = float(calculated[name])
        expected_value = float(expected)
        abs_error = abs(actual - expected_value)
        # Tolerancia extremadamente pequeña: solo protege el congelamiento de
        # la referencia analítica, no es la tolerancia OpenDSS del benchmark.
        freeze_tolerance = 1e-9 * max(1.0, abs(expected_value))
        metrics[name] = {
            "calculated": actual,
            "frozen": expected_value,
            "abs_error": abs_error,
            "freeze_tolerance": freeze_tolerance,
            "pass": abs_error <= freeze_tolerance,
        }
    return {
        "metrics": metrics,
        "pass": all(item["pass"] for item in metrics.values()),
    }


def run() -> dict[str, Any]:
    manifest = _load_manifest()
    inputs = dict(manifest["inputs"])
    case = {
        "id": manifest["id"],
        "description": manifest["title"],
        **inputs,
    }

    benchmark = benchmarks.run_case(case)
    frozen_check = _frozen_reference_consistency(
        benchmark["reference"], manifest["expected_reference"]
    )

    tolerances_match = manifest["tolerances"] == benchmarks.TOLERANCES
    passed = bool(benchmark["pass"] and frozen_check["pass"] and tolerances_match)

    return {
        "schema": "MCP_ELECTRICO_REFERENCE_RESULT_V1",
        "id": manifest["id"],
        "pass": passed,
        "reference": {
            "method": manifest["reference_method"],
            "depends_on_opendss": False,
            "frozen_expected": manifest["expected_reference"],
            "recalculated": benchmark["reference"],
            "frozen_consistency": frozen_check,
        },
        "engine_under_test": "OpenDSS",
        "actual": benchmark["actual"],
        "comparisons": benchmark["comparisons"],
        "tolerances": manifest["tolerances"],
        "tolerances_match_p1": tolerances_match,
        "inputs": inputs,
        "professional_emission": False,
        "limitations": manifest["limitations"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Caso canónico REF-01")
    parser.add_argument(
        "--output",
        default="resultado_caso_referencia_01.json",
        help="Ruta del JSON de salida",
    )
    args = parser.parse_args()

    result = run()
    target = Path(args.output).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"id": result["id"], "pass": result["pass"], "output": str(target)}, ensure_ascii=False))
    if not result["pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
