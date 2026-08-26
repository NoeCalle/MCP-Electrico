"""Smoke test integral para el primer clon de MCP Eléctrico.

Construye una red MT/BT pequeña mediante las mismas funciones que usa el
servidor MCP, ejecuta flujo OpenDSS, analiza caída de tensión, comprueba el gate
P3 y genera un workspace HTML más un resumen JSON reproducible.

Uso:
    python examples/primer_uso.py
    python examples/primer_uso.py --output-dir salida_primer_uso
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import server
from mcp_electrico import p3_completion, validation_status


def _version(package: str) -> str:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return "NOT_INSTALLED"


def run(output_dir: str | Path = ".") -> dict[str, Any]:
    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    workspace_path = out / "workspace_primer_uso.html"
    result_path = out / "resultado_primer_uso.json"

    server.configurar_workspace(
        str(workspace_path),
        titulo="MCP Eléctrico — Primer uso",
        auto_regenerar=True,
    )

    # Caso deliberadamente pequeño y estable: red 22.9/0.48 kV con dos cargas.
    server.crear_circuito("primer_uso", 22.9)
    server.agregar_transformador(
        "tr_01",
        "sourcebus",
        "tgbt",
        kva=500,
        kv_primario=22.9,
        kv_secundario=0.48,
        conexion_primario="delta",
        conexion_secundario="wye",
    )
    server.agregar_linea(
        "f_motor",
        "tgbt",
        "mcc_01",
        0.035,
        r1_ohm_km=0.25,
        x1_ohm_km=0.12,
    )
    server.agregar_linea(
        "f_critico",
        "tgbt",
        "tcrit_01",
        0.040,
        r1_ohm_km=0.22,
        x1_ohm_km=0.11,
    )
    server.agregar_carga(
        "motor_bomba",
        "mcc_01",
        75,
        30,
        kv=0.48,
        tipo_visual="motor",
    )
    server.agregar_carga(
        "cargas_criticas",
        "tcrit_01",
        80,
        25,
        kv=0.48,
        critica=True,
        tipo_visual="tablero",
    )

    server.configurar_etiqueta_carga_unifilar("motor_bomba", "M-01 · BOMBA AGUA")
    server.configurar_etiqueta_carga_unifilar("cargas_criticas", "TABLERO CRÍTICO")
    server.configurar_alimentador_unifilar(
        "Line.f_motor",
        etiqueta="F-01",
        proteccion="mccb",
        conductor="3x70 mm2 Cu XLPE",
        corriente_nominal_a=160,
        capacidad_ruptura_ka=25,
    )
    server.configurar_alimentador_unifilar(
        "Line.f_critico",
        etiqueta="F-02",
        proteccion="mccb",
        conductor="3x50 mm2 Cu XLPE",
        corriente_nominal_a=125,
        capacidad_ruptura_ka=25,
    )

    power_flow = server.ejecutar_flujo_potencia()
    voltage_drop = server.analizar_caida_tension(limite_pct=3.0)
    workspace_state = server.obtener_estado_workspace()

    p3_gate = p3_completion.evaluar_cierre_p3()
    maturity = {
        module: validation_status.get_module_status(module)
        for module in ("power_flow", "voltage_drop", "ampacity", "short_circuit")
    }

    checks = {
        "opendss_converged": bool(power_flow.get("convergio")),
        "workspace_generated": workspace_path.exists(),
        "p3_closed": p3_gate.get("phase_status") == "READY_WITH_LIMITATIONS",
        "p4_formally_unblocked": p3_gate.get("ready_for_next_phase") is True
        and p3_gate.get("next_phase") == "P4_IEC_60909",
        "ampacity_maturity_consistent": maturity["ampacity"].get("status")
        == "VALIDATED_WITH_LIMITATIONS",
        "iec60909_not_falsely_claimed": maturity["short_circuit"].get("status")
        == "UNDER_VALIDATION",
    }
    ok = all(checks.values())

    result: dict[str, Any] = {
        "schema": "MCP_ELECTRICO_FIRST_RUN_V1",
        "ok": ok,
        "checks": checks,
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "opendssdirect.py": _version("opendssdirect.py"),
            "mcp": _version("mcp"),
            "pandapower": _version("pandapower"),
        },
        "engine_policy": {
            "executed_engine": "OpenDSS",
            "automatic_dispatch": False,
            "crosscheck": False,
            "pandapower_executed": False,
        },
        "maturity": maturity,
        "p3_gate": {
            "phase_status": p3_gate.get("phase_status"),
            "ready_for_next_phase": p3_gate.get("ready_for_next_phase"),
            "next_phase": p3_gate.get("next_phase"),
            "professional_emission": p3_gate.get("professional_emission"),
            "pending_criteria": p3_gate.get("pending_criteria"),
        },
        "power_flow": power_flow,
        "voltage_drop": voltage_drop,
        "workspace_state": workspace_state,
        "outputs": {
            "workspace_html": str(workspace_path),
            "result_json": str(result_path),
        },
        "limitations": [
            "Este smoke test comprueba instalación e integración; no constituye un estudio profesional.",
            "El límite de caída de tensión de 3 % es un parámetro del ejemplo, no una regla normativa universal.",
            "El cortocircuito IEC 60909 todavía pertenece a P4 y no se ejecuta en este smoke test.",
        ],
    }

    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Primer smoke test de MCP Eléctrico")
    parser.add_argument(
        "--output-dir",
        default="salida_primer_uso",
        help="Directorio donde se generan HTML y JSON (default: salida_primer_uso)",
    )
    args = parser.parse_args()

    result = run(args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    if not result["ok"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
