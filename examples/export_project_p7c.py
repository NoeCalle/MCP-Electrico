"""Genera un reporte técnico P7C reproducible para CI/demostración."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp_electrico import core, project_report, project_snapshot, workspace_state


def build_case() -> None:
    core.crear_circuito("p7c_ci_demo", 0.48)
    workspace_state.reset_for_circuit("p7c_ci_demo")
    core.agregar_linea(
        "f1",
        "sourcebus",
        "bus1",
        0.05,
        fases=3,
        r1_ohm_km=0.20,
        x1_ohm_km=0.08,
    )
    workspace_state.mark_model_changed("p7c_ci_add_f1")
    core.agregar_carga("load1", "bus1", 60.0, 15.0, fases=3, kv=0.48)
    workspace_state.mark_model_changed("p7c_ci_add_load1")
    workspace_state.record_solution(
        {"convergio": True, "status": "CI_REPRODUCIBLE_SOLUTION"},
        "powerflow",
        "p7c_ci_solution",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="project_report_p7c.html")
    parser.add_argument("--snapshot-output", default="project_report_p7c_snapshot.json")
    parser.add_argument("--netlist-dir", default="project_report_p7c_dss")
    args = parser.parse_args()

    output_path = Path(args.output).expanduser().resolve()
    snapshot_output_path = Path(args.snapshot_output).expanduser().resolve()
    netlist_dir = Path(args.netlist_dir).expanduser().resolve()

    build_case()
    snapshot = project_snapshot.construir_snapshot(str(netlist_dir))
    verification = project_snapshot.verificar_snapshot(snapshot)
    if not verification.get("ok"):
        raise SystemExit(f"Snapshot P7A inválido: {verification}")

    snapshot_output_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    result = project_report.exportar_reporte(snapshot, str(output_path))
    if not result.get("ok"):
        raise SystemExit(f"Reporte P7C bloqueado: {result}")

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
