"""Genera un snapshot P7A reproducible para CI/demostración."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp_electrico import core, project_snapshot, workspace_state


def build_case() -> None:
    core.crear_circuito("p7a_ci_demo", 0.48)
    workspace_state.reset_for_circuit("p7a_ci_demo")
    core.agregar_linea(
        "f1",
        "sourcebus",
        "bus1",
        0.05,
        fases=3,
        r1_ohm_km=0.20,
        x1_ohm_km=0.08,
    )
    workspace_state.mark_model_changed("p7a_ci_add_f1")
    core.agregar_carga("load1", "bus1", 60.0, 15.0, fases=3, kv=0.48)
    workspace_state.mark_model_changed("p7a_ci_add_load1")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="project_p7a.json")
    parser.add_argument("--netlist-dir", default="project_p7a_dss")
    args = parser.parse_args()

    build_case()
    snapshot = project_snapshot.construir_snapshot(args.netlist_dir)
    verification = project_snapshot.verificar_snapshot(snapshot)
    if not verification.get("ok"):
        raise SystemExit(f"Snapshot P7A inválido: {verification}")

    target = Path(args.output)
    target.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps({
        "path": str(target),
        "hash": snapshot["hash"],
        "verification": verification,
        "professional_emission": snapshot["professional_emission"],
    }, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
