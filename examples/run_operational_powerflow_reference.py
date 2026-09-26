"""Ejercicio operativo de flujo de carga sobre el caso controlado MCP-REF-SUB-01.

No introduce una fase nueva. Reutiliza el intake, readiness y ejecución controlada
P8/P10 para mostrar una salida de ingeniería compacta y auditable.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp_electrico import (
    real_controlled_execution,
    real_integrated_readiness,
    real_pilot_intake,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "examples" / "p10_reference_substation_stage1.json"
SCHEMA = "MCP_ELECTRICO_OPERATIONAL_POWERFLOW_EXERCISE_V1"


def _load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _input_totals(manifest: dict[str, Any]) -> dict[str, float | None]:
    loads = (manifest.get("topology") or {}).get("loads") or []
    kw = sum(float(item.get("kw") or 0.0) for item in loads if isinstance(item, dict))
    kvar = sum(float(item.get("kvar") or 0.0) for item in loads if isinstance(item, dict))
    kva = math.hypot(kw, kvar)
    return {
        "connected_kw": round(kw, 3),
        "connected_kvar": round(kvar, 3),
        "connected_kva": round(kva, 3),
        "aggregate_pf": round(kw / kva, 5) if kva > 0 else None,
    }


def ejecutar(path: Path) -> dict[str, Any]:
    manifest = _load_manifest(path)

    intake = real_pilot_intake.evaluar_admision(manifest)
    if intake.get("ready_to_build_model") is not True:
        raise RuntimeError(f"Intake bloqueado: {intake.get('issues')}")

    readiness = real_integrated_readiness.evaluar_readiness_integral(manifest)
    if readiness.get("all_requested_ready") is not True:
        raise RuntimeError(
            f"Readiness bloqueado: {readiness.get('blocked_scopes')} "
            f"{readiness.get('scope_readiness')}"
        )

    execution = real_controlled_execution.ejecutar_controlado(manifest)
    if execution.get("execution_status") != real_controlled_execution.STATUS_COMPLETED:
        raise RuntimeError(
            f"Ejecución no completada: {execution.get('execution_status')} "
            f"pending={execution.get('pending_scopes')}"
        )

    power = execution["results"]["POWER_FLOW"]
    voltage = execution["results"]["VOLTAGE_DROP"]

    if power.get("convergio") is not True or voltage.get("convergio") is not True:
        raise RuntimeError("OpenDSS no convergió en flujo/caída de tensión.")

    buses = [
        {
            "bus": item.get("bus"),
            "vpu_min": item.get("vpu_min"),
            "vpu_average": item.get("vpu_promedio"),
            "vpu_max": item.get("vpu_max"),
        }
        for item in power.get("buses") or []
    ]

    feeders_by_id = {
        str(item.get("id")): item for item in power.get("alimentadores") or []
    }
    drops_by_id = {
        str(item.get("id")): item for item in voltage.get("alimentadores") or []
    }
    feeder_ids = sorted(set(feeders_by_id) | set(drops_by_id))
    feeders = []
    for identifier in feeder_ids:
        flow = feeders_by_id.get(identifier) or {}
        drop = drops_by_id.get(identifier) or {}
        feeders.append(
            {
                "id": identifier,
                "from_bus": flow.get("bus1") or drop.get("bus_origen"),
                "to_bus": flow.get("bus2") or drop.get("bus_destino"),
                "length_km": flow.get("longitud_km"),
                "current_max_a": flow.get("corriente_max_a"),
                "flow_kw_terminal1": flow.get("flujo_kw_terminal1"),
                "flow_kvar_terminal1": flow.get("flujo_kvar_terminal1"),
                "voltage_drop_pct": drop.get("caida_evaluada_pct"),
                "voltage_drop_status": drop.get("estado_criterio"),
            }
        )

    project = manifest.get("project") or {}
    source = manifest.get("source") or {}
    summary = {
        "schema": SCHEMA,
        "project": {
            "id": project.get("id"),
            "name": project.get("name"),
            "source_reference": project.get("source_reference"),
        },
        "source": {
            "bus": source.get("bus"),
            "kv_ll": source.get("kv_ll"),
            "frequency_hz": source.get("frequency_hz"),
        },
        "requested_scope": execution.get("requested_scopes"),
        "executed_scope": execution.get("executed_scopes"),
        "input_totals": _input_totals(manifest),
        "power_flow": {
            "engine": "OpenDSS",
            "converged": True,
            "losses_kw": power.get("resumen", {}).get("perdidas_totales_kw"),
            "losses_kvar": power.get("resumen", {}).get("perdidas_totales_kvar"),
            "buses": buses,
            "feeders": feeders,
        },
        "voltage_drop": {
            "criterion_limit_pct": voltage.get("criterio", {}).get("limite_pct"),
            "criterion_origin": voltage.get("criterio", {}).get("origen"),
            "universal_normative_claim": voltage.get("criterio", {}).get(
                "normativo_universal"
            ),
            "system_min_vpu": voltage.get("resumen", {}).get("vpu_min_sistema"),
            "feeders_evaluated": voltage.get("resumen", {}).get(
                "alimentadores_evaluados"
            ),
            "feeders_exceeding": voltage.get("resumen", {}).get(
                "alimentadores_que_exceden"
            ),
            "worst_feeder_id": voltage.get("resumen", {}).get(
                "peor_alimentador_id"
            ),
            "worst_drop_pct": voltage.get("resumen", {}).get("peor_caida_pct"),
        },
        "boundaries": {
            "automatic_defaults": False,
            "automatic_dispatch": False,
            "crosscheck": False,
            "professional_emission": False,
        },
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Manifiesto P8/P10 compatible.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Ruta JSON opcional para guardar el resumen.",
    )
    args = parser.parse_args()

    result = ejecutar(args.manifest)
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    print(rendered)

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
