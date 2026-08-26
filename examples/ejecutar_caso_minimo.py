"""Ejecuta un caso mínimo declarativo V1 desde JSON.

Uso:
    python examples/ejecutar_caso_minimo.py
    python examples/ejecutar_caso_minimo.py mi_caso.json --output-dir salida
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp_electrico.minimal_case import MinimalCaseError, cargar_caso, ejecutar_caso


def main() -> None:
    parser = argparse.ArgumentParser(description="Ejecutar caso mínimo JSON de MCP Eléctrico")
    parser.add_argument(
        "input",
        nargs="?",
        default=str(ROOT / "examples" / "caso_minimo.json"),
        help="Archivo JSON de entrada (default: examples/caso_minimo.json)",
    )
    parser.add_argument(
        "--output-dir",
        default="salida_caso_minimo",
        help="Carpeta de resultados (default: salida_caso_minimo)",
    )
    args = parser.parse_args()

    try:
        case = cargar_caso(args.input)
        result = ejecutar_caso(case, args.output_dir)
    except MinimalCaseError as exc:
        print(f"CASO MÍNIMO INVÁLIDO: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    except Exception as exc:
        print(f"ERROR DE EJECUCIÓN: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(3) from exc

    summary = {
        "schema": result["schema"],
        "ok": result["ok"],
        "case_id": result["case_id"],
        "input_sha256": result["input_sha256"],
        "fixed_scope": result["fixed_scope"],
        "engine_policy": result["engine_policy"],
        "counts": result["counts"],
        "outputs": result["outputs"],
        "professional_emission": result["professional_emission"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise SystemExit(4)


if __name__ == "__main__":
    main()
