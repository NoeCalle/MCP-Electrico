"""Genera evidencia CI de reconstrucción verificable P7B."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mcp_electrico import core, project_reconstruction, project_snapshot, workspace_state


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="reconstruction_p7b.json")
    parser.add_argument("--source-netlist", default="p7b_ci_source_dss")
    parser.add_argument("--reconstructed", default="p7b_ci_reconstructed")
    args = parser.parse_args()

    # OpenDSS puede cambiar el cwd durante Save/Compile. Resolver todas las
    # rutas antes de tocar el motor evita que una salida relativa termine en
    # otro directorio aunque la reconstrucción sea correcta.
    output_path = Path(args.output).expanduser().resolve()
    source_netlist_path = Path(args.source_netlist).expanduser().resolve()
    reconstructed_path = Path(args.reconstructed).expanduser().resolve()

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
    snapshot = project_snapshot.construir_snapshot(str(source_netlist_path))

    core.crear_circuito("p7b_ci_sentinel", 0.22)
    workspace_state.reset_for_circuit("p7b_ci_sentinel")

    result = project_reconstruction.reconstruir_snapshot(
        snapshot,
        directorio_reconstruccion=str(reconstructed_path),
    )
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    # El ejemplo solo genera evidencia. El gate del workflow valida el
    # contrato estructurado y muestra el resultado completo si algo difiere.
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
