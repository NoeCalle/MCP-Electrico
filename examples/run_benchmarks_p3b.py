"""Genera evidencia P3B de infraestructura numérica.

IMPORTANTE: los casos actuales usan una reproducción secundaria del CNE.
El benchmark valida lookup exacto, trazabilidad y política de seguridad, no
certifica todavía los valores normativos para emisión profesional.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp_electrico import ampacity_datasets


CASES = ROOT / "mcp_electrico" / "data" / "ampacity_p3b_benchmark_cases.json"
OUTPUT = ROOT / "benchmark_p3b.json"


def run() -> dict:
    fixture = json.loads(CASES.read_text(encoding="utf-8"))
    results = []
    passed = 0

    for case in fixture["cases"]:
        actual = ampacity_datasets.resolver_factor(
            case["dataset_id"],
            installation_method=case["installation_method"],
            circuits_grouped=case["circuits_grouped"],
            arrangement_id=case["arrangement_id"],
            allow_secondary=True,
        )
        factor = actual.get("factor")
        expected = float(case["expected_factor"])
        ok = (
            actual.get("status") == "RESOLVED_SECONDARY"
            and factor is not None
            and abs(float(factor) - expected) <= 1e-12
            and actual.get("professional_emission") is False
        )
        passed += int(ok)
        results.append({
            "id": case["id"],
            "expected_factor": expected,
            "actual_factor": factor,
            "status": actual.get("status"),
            "professional_emission": actual.get("professional_emission"),
            "pass": ok,
        })

    total = len(results)
    payload = {
        "suite": "P3B_NUMERIC_DATASET_INFRASTRUCTURE",
        "evidence_level": fixture["evidence_level"],
        "source": fixture["source"],
        "professional_emission": False,
        "scope": "exact lookup de valores secundarios predeclarados; no valida norma primaria",
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass": passed == total,
        },
        "cases": results,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = run()
    print(json.dumps(result["summary"]))
    raise SystemExit(0 if result["summary"]["pass"] else 1)
