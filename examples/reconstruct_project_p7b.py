"""Genera evidencia CI de reconstrucción verificable P7B."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from mcp_electrico import core, project_reconstruction, project_snapshot, workspace_state


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="reconstruction_p7b.json")
    parser.add_argument("--source-netlist", default="p7b_ci_source_dss")
    parser.add_argument("--reconstructed", default="p7b_ci_reconstructed")
    args = parser.parse_args()

    core.crear_circuito("p7b_ci_source", 0.48)
    workspace_state.reset_for_circuit("p7b_ci_source")
    core.agregar_linea(
        "f1", "sourcebus", "bus1", 0.05,
        fases=3, r1_ohm_km=0.20, x1_ohm_km=0.08,
    )
    workspace_state.mark_model_changed("p7b_ci_add_f1")
    core.agregar_carga("load1", "bus1", 60.0, 15.0, fases=3, kv=0.48)
    workspace_state.mark_model_changed("p7b_ci_add_load1")
    workspace_state.record_study(
        "historical_ci_probe",
        {"status": "STORED_ONLY", "professional_emission": False},
        "p7b_ci_probe",
    )
    snapshot = project_snapshot.construir_snapshot(args.source_netlist)

    core.crear_circuito("p7b_ci_sentinel", 0.22)
    workspace_state.reset_for_circuit("p7b_ci_sentinel")

    result = project_reconstruction.reconstruir_snapshot(
        snapshot,
        directorio_reconstruccion=args.reconstructed,
    )
    Path(args.output).write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    if result.get("status") != "RECONSTRUCTED_NETLIST_VERIFIED_WITH_REBIND_REQUIRED":
        raise SystemExit(f"P7B reconstruction failed: {result}")
    if not (result.get("roundtrip") or {}).get("canonical_netlist_match"):
        raise SystemExit("P7B round-trip canonical netlist mismatch")
    if result.get("stored_results_promoted_to_current") is not False:
        raise SystemExit("P7B promoted stored results unexpectedly")
    if result.get("professional_emission") is not False:
        raise SystemExit("P7B professional emission must remain false")


if __name__ == "__main__":
    main()
