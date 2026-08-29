"""P8A — piloto integral reproducible de una subestación MT/BT.

Caso SINTÉTICO pero técnicamente realista para recorrer MCP Eléctrico 0.9 de
punta a punta. No representa una instalación existente, no usa curvas de
fabricante y mantiene ``professional_emission=false``.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import server
from mcp_electrico import (
    ampacity,
    conductor_library,
    core,
    iec60909,
    iec60909_single_phase_ground,
    iec60909_suite,
    p7_completion,
    professional_data,
    project_report,
    project_snapshot,
    protection_checks,
    protection_clearing_time,
    protection_coordination,
    protection_curves,
    protection_data,
    workspace_state,
    zero_sequence,
)

SCHEMA = "MCP_ELECTRICO_P8A_SUBSTATION_PILOT_V1"
CASE_ID = "P8A_SYNTHETIC_22K9_0K48_SUBSTATION_V1"
TEMPERATURES_MIN = {
    "Line.mt_feeder": 90.0,
    "Line.lv_main": 90.0,
    "Line.lv_crit": 90.0,
}


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def _reset() -> None:
    professional_data.reset()
    zero_sequence.reset()
    conductor_library.reset()
    ampacity.reset()
    protection_data.reset()
    protection_curves.reset()


def _register_breaker(
    name: str,
    element: str,
    in_a: float,
    curve_id: str,
    dataset_id: str,
    points: list[dict[str, float]],
) -> None:
    protection_data.definir_dispositivo(
        nombre=name,
        tipo="circuit_breaker",
        elemento_protegido=element,
        in_a=in_a,
        ue_kv=0.48,
        fabricante="PILOT_TEST_DATA",
        modelo=f"SYNTHETIC_{name}",
        polos=3,
        norma_referencia="IEC 60947-2:2024 — referencia objetivo P5C",
        icu_ka=36.0,
        ics_ka=25.0,
        fuente_referencia="P8A synthetic rating; replace with approved project datasheet",
    )
    protection_data.vincular_curva(
        name,
        curva_id=curve_id,
        tipo_curva="TEST_CURVE",
        fuente_referencia="P8A synthetic TEST_DATA; not manufacturer data",
        revision="P8A-v1",
    )
    protection_curves.registrar_dataset(
        dataset_id=dataset_id,
        curve_id=curve_id,
        shape="BAND",
        time_semantics="TOTAL_CLEARING_TIME",
        segments=[{"id": "pilot_band", "points": points}],
        source_type="TEST_DATA",
        source_reference="P8A synthetic coordination dataset; no manufacturer claim",
        revision="P8A-v1",
    )
    protection_curves.vincular_dataset_dispositivo(name, dataset_id)


def _register_protection() -> None:
    _register_breaker(
        "QF_MAIN_LV",
        "Line.lv_main",
        630.0,
        "P8A_QF_MAIN_TEST_CURVE",
        "P8A_QF_MAIN_TEST_DATASET",
        [
            {"current_a": 630.0, "time_min_s": 15.0, "time_max_s": 18.0},
            {"current_a": 1500.0, "time_min_s": 4.0, "time_max_s": 5.0},
            {"current_a": 5000.0, "time_min_s": 0.80, "time_max_s": 1.00},
            {"current_a": 20000.0, "time_min_s": 0.25, "time_max_s": 0.30},
            {"current_a": 50000.0, "time_min_s": 0.12, "time_max_s": 0.15},
        ],
    )
    _register_breaker(
        "QF_CRIT_LV",
        "Line.lv_crit",
        400.0,
        "P8A_QF_CRIT_TEST_CURVE",
        "P8A_QF_CRIT_TEST_DATASET",
        [
            {"current_a": 400.0, "time_min_s": 10.0, "time_max_s": 12.0},
            {"current_a": 1000.0, "time_min_s": 2.0, "time_max_s": 2.4},
            {"current_a": 5000.0, "time_min_s": 0.15, "time_max_s": 0.18},
            {"current_a": 20000.0, "time_min_s": 0.040, "time_max_s": 0.050},
            {"current_a": 50000.0, "time_min_s": 0.025, "time_max_s": 0.030},
        ],
    )


def _build_model(out: Path) -> dict[str, Any]:
    workspace_path = out / "p8a_workspace_v5.html"
    server.configurar_workspace(
        str(workspace_path),
        titulo="P8A — Subestación 22.9/0.48 kV · Engineering Preview",
        auto_regenerar=True,
    )
    server.crear_circuito("p8a_substation", 22.9)
    _reset()

    source = professional_data.definir_red_equivalente(
        kv_ll=22.9,
        scc_max_mva=350.0,
        x_r_max=10.0,
        scc_min_mva=180.0,
        x_r_min=6.0,
        escenario_activo="max",
        fuente_referencia="P8A synthetic utility equivalent",
    )
    zero_sequence.definir_fuente(
        r0_max_ohm=0.15,
        x0_max_ohm=0.45,
        r0_min_ohm=0.25,
        x0_min_ohm=0.80,
        fuente_referencia="P8A synthetic utility Z0",
    )

    core.agregar_linea(
        "mt_feeder", "sourcebus", "se_mt", 0.15,
        fases=3, r1_ohm_km=0.20, x1_ohm_km=0.10,
    )
    mt_conductor = conductor_library.aplicar_conductor(
        "Line.mt_feeder",
        "NEXANS-N2XSY-18-30-CU-70-PH16",
        "air_trefoil_30c",
    )
    zero_sequence.definir_linea(
        "Line.mt_feeder", 0.60, 0.30, 250.0,
        fuente_referencia="P8A synthetic explicit MT Z0/C0",
    )

    transformer = professional_data.agregar_transformador_profesional(
        nombre="tr_01",
        bus_hv="se_mt",
        bus_lv="tgbt",
        kva=1000.0,
        kv_hv=22.9,
        kv_lv=0.48,
        uk_percent=6.0,
        grupo_vectorial="Dyn11",
        x_r=10.0,
        no_load_loss_kw=1.8,
        i0_percent=0.6,
        fabricante="PILOT_TEST_DATA",
        modelo="SYNTHETIC_1000KVA_DYN11",
        fuente_referencia="P8A synthetic transformer nameplate",
    )
    zero_sequence.definir_transformador(
        "Transformer.tr_01",
        uk0_percent=5.5,
        ur0_percent=0.6,
        magnetizing_z0_ratio_percent=100.0,
        magnetizing_r_over_x=0.0,
        leakage_share_hv=0.5,
        neutral_side="lv",
        neutral_mode="solid",
        fuente_referencia="P8A synthetic transformer Z0/neutral",
    )

    core.agregar_linea(
        "lv_main", "tgbt", "db_main", 0.025,
        fases=3, r1_ohm_km=0.08, x1_ohm_km=0.07,
    )
    zero_sequence.definir_linea(
        "Line.lv_main", 0.24, 0.12, 100.0,
        fuente_referencia="P8A synthetic LV main Z0/C0",
    )
    core.agregar_linea(
        "lv_crit", "db_main", "crit_bus", 0.040,
        fases=3, r1_ohm_km=0.12, x1_ohm_km=0.08,
    )
    zero_sequence.definir_linea(
        "Line.lv_crit", 0.36, 0.15, 100.0,
        fuente_referencia="P8A synthetic LV critical Z0/C0",
    )
    core.agregar_carga("load_general", "db_main", 120.0, 40.0, fases=3, kv=0.48)
    core.agregar_carga("load_critical", "crit_bus", 250.0, 80.0, fases=3, kv=0.48)

    server.configurar_etiqueta_carga_unifilar("load_general", "DB-MAIN · CARGA GENERAL")
    server.configurar_etiqueta_carga_unifilar("load_critical", "DB-CRIT · CARGA CRÍTICA")
    # IMPORTANTE: el conductor visual MT conserva exactamente la descripción
    # canónica de la asignación P2. Cambiarla aquí invalidaría trazabilidad P3.
    server.configurar_alimentador_unifilar(
        "Line.mt_feeder",
        etiqueta="MT-01",
        proteccion="breaker",
        conductor=mt_conductor["descripcion"],
        corriente_nominal_a=40.0,
        capacidad_ruptura_ka=25.0,
    )
    server.configurar_alimentador_unifilar(
        "Line.lv_main",
        etiqueta="LV-01",
        proteccion="mccb",
        conductor="P8A LV MAIN · sección por validar en proyecto real",
        corriente_nominal_a=630.0,
        capacidad_ruptura_ka=36.0,
    )
    server.configurar_alimentador_unifilar(
        "Line.lv_crit",
        etiqueta="LV-02",
        proteccion="mccb",
        conductor="P8A LV CRIT · 240 mm² para check térmico explícito",
        corriente_nominal_a=400.0,
        capacidad_ruptura_ka=36.0,
    )

    ampacity.definir_condiciones(
        nombre_elemento="Line.mt_feeder",
        norma_id="IEC_60364_5_52_2009_A1_2024",
        in_proteccion_a=40.0,
        confirmar_condiciones_base=True,
        ib_diseno_a=25.0,
        referencia_in="P8A synthetic MT protection schedule",
        referencia_ib="P8A explicit design current",
        referencia_condiciones_instalacion=(
            "P8A confirms catalog air/trefoil/30 C base condition only for product-flow testing; "
            "replace with project evidence"
        ),
    )
    _register_protection()
    workspace_state.mark_model_changed("p8a_complete_model_and_engineering_data")
    return {
        "workspace_path": workspace_path,
        "source": source,
        "mt_conductor": mt_conductor,
        "transformer": transformer,
    }


def _p5_checks(fault_3ph: dict[str, Any], fault_main: dict[str, Any]) -> dict[str, Any]:
    fault_crit_ka = float(fault_3ph["scenarios"]["max"]["results"]["ikss_ka"])
    fault_main_ka = float(fault_main["results"]["ikss_ka"])
    fault_a = fault_crit_ka * 1000.0

    tcc = protection_curves.evaluar_dispositivo("QF_CRIT_LV", fault_a)
    clearing_down = protection_clearing_time.evaluar_tiempo_despeje("QF_CRIT_LV", fault_a)
    clearing_up = protection_clearing_time.evaluar_tiempo_despeje("QF_MAIN_LV", fault_a)
    breaking_down = protection_checks.evaluar_capacidad_corte(
        "QF_CRIT_LV", fault_crit_ka, 0.48,
        fuente_corriente="P8A IEC 60909 3F MAX at crit_bus",
        tipo_falla="3ph", escenario="max",
    )
    breaking_up = protection_checks.evaluar_capacidad_corte(
        "QF_MAIN_LV", fault_main_ka, 0.48,
        fuente_corriente="P8A IEC 60909 3F MAX at db_main",
        tipo_falla="3ph", escenario="max",
    )
    conservative_time = float(clearing_down["clearing_time"]["conservative_time_s"])
    thermal = protection_checks.evaluar_soportabilidad_termica_conductor(
        elemento="Line.lv_crit",
        corriente_falla_ka=fault_crit_ka,
        tiempo_despeje_s=conservative_time,
        seccion_mm2=240.0,
        k_a_sqrt_s_per_mm2=143.0,
        fuente_k="P8A explicit synthetic k; verify before professional use",
        fuente_tiempo="P8A P5D conservative clearing time from TEST_DATA",
        fuente_seccion="P8A synthetic cable schedule: 240 mm²",
    )
    coordination = protection_coordination.evaluar_coordinacion_temporal(
        dispositivo_downstream="QF_CRIT_LV",
        corriente_downstream_a=fault_a,
        dispositivo_upstream="QF_MAIN_LV",
        corriente_upstream_a=fault_a,
        margen_minimo_s=0.10,
        fuente_relacion="P8A declared radial QF_MAIN_LV -> QF_CRIT_LV",
        fuente_corrientes="P8A explicit through-current for 3F fault at crit_bus",
    )
    return {
        "tcc": tcc,
        "clearing_down": clearing_down,
        "clearing_up": clearing_up,
        "breaking_down": breaking_down,
        "breaking_up": breaking_up,
        "thermal": thermal,
        "coordination": coordination,
    }


def run(output_dir: str | Path = "salida_p8a_substation") -> dict[str, Any]:
    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "workspace": out / "p8a_workspace_v5.html",
        "snapshot": out / "p8a_project_snapshot.json",
        "report": out / "p8a_technical_report.html",
        "summary": out / "p8a_pilot_summary.json",
        "netlist": out / "p8a_netlist_dss",
    }
    model = _build_model(out)

    power_flow = server.ejecutar_flujo_potencia()
    voltage_drop = server.analizar_caida_tension(limite_pct=5.0)
    p3 = ampacity.evaluar("Line.mt_feeder")
    workspace_state.record_study("ampacity", p3, action="p8a_ampacity")

    fault_3ph = iec60909_suite.ejecutar_3ph_max_min(
        "crit_bus", line_endtemp_degree_c=TEMPERATURES_MIN
    )
    workspace_state.record_study("iec60909_3ph", fault_3ph, action="p8a_iec60909_3ph")
    fault_main = iec60909.ejecutar_3ph("max", "db_main")
    fault_1ph_max = iec60909_single_phase_ground.ejecutar_1ph_ground("crit_bus", "max")
    fault_1ph_min = iec60909_single_phase_ground.ejecutar_1ph_ground(
        "crit_bus", "min", line_endtemp_degree_c=TEMPERATURES_MIN
    )
    fault_1ph = {
        "schema": "MCP_ELECTRICO_P8A_1PH_GROUND_PAIR_V1",
        "max": fault_1ph_max,
        "min": fault_1ph_min,
        "professional_emission": False,
    }
    workspace_state.record_study("iec60909_1ph_ground", fault_1ph, action="p8a_1ph")

    p5 = _p5_checks(fault_3ph, fault_main)
    workspace_state.record_study("protection_tcc_evaluation", p5["tcc"], action="p8a_tcc")
    workspace_state.record_study(
        "protection_breaking_capacity",
        {"downstream": p5["breaking_down"], "upstream": p5["breaking_up"]},
        action="p8a_breaking",
    )
    workspace_state.record_study("protection_conductor_thermal", p5["thermal"], action="p8a_thermal")
    workspace_state.record_study(
        "protection_clearing_time",
        {"downstream": p5["clearing_down"], "upstream": p5["clearing_up"]},
        action="p8a_clearing",
    )
    workspace_state.record_study("protection_coordination", p5["coordination"], action="p8a_coordination")
    server.regenerar_workspace()

    snapshot = project_snapshot.construir_snapshot(str(paths["netlist"]))
    verification = project_snapshot.verificar_snapshot(snapshot)
    _write_json(paths["snapshot"], snapshot)
    report = project_report.exportar_reporte(snapshot, str(paths["report"]))
    p7d = p7_completion.evaluar_cierre_p7()

    checks = {
        "engineering_preview_gate": p7d.get("engineering_preview_ready") is True,
        "power_flow_converged": bool(power_flow.get("convergio")),
        "p3_ampacity_pass": p3.get("status") == "CUMPLE",
        "p4_3ph_max_min": bool(fault_3ph.get("ok"))
        and fault_3ph["scenarios"]["max"]["results"]["ikss_ka"]
        > fault_3ph["scenarios"]["min"]["results"]["ikss_ka"] > 0,
        "p4_1ph_ground_max_min": bool(fault_1ph_max.get("ok"))
        and bool(fault_1ph_min.get("ok")),
        "p5_breaking_capacity": p5["breaking_down"].get("status") == "PASS"
        and p5["breaking_up"].get("status") == "PASS",
        "p5_clearing_time": p5["clearing_down"].get("status") == "CLEARING_TIME_READY"
        and p5["clearing_up"].get("status") == "CLEARING_TIME_READY",
        "p5_conductor_thermal": p5["thermal"].get("status") == "PASS",
        "p5_temporal_coordination": p5["coordination"].get("status") == "PASS",
        "workspace_v5_written": paths["workspace"].exists(),
        "snapshot_hash_match": verification.get("status") == "HASH_MATCH",
        "technical_report_written": bool(report.get("ok")) and Path(report["path"]).exists(),
        "arc_flash_deferred": p7d.get("arc_flash_ieee1584") == "DEFERRED",
        "professional_emission_closed": p7d.get("professional_emission") is False,
    }
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "case_id": CASE_ID,
        "case_kind": "SYNTHETIC_REALISTIC_PRODUCT_PILOT",
        "ok": all(checks.values()),
        "checks": checks,
        "model": {
            "nominal_system": "22.9/0.48 kV",
            "utility_source": model["source"],
            "mt_conductor": model["mt_conductor"],
            "transformer": model["transformer"],
        },
        "studies": {
            "power_flow": power_flow,
            "voltage_drop": voltage_drop,
            "ampacity_p3": p3,
            "iec60909_3ph": fault_3ph,
            "iec60909_1ph_ground": fault_1ph,
            "breaking_capacity": {"downstream": p5["breaking_down"], "upstream": p5["breaking_up"]},
            "clearing_time": {"downstream": p5["clearing_down"], "upstream": p5["clearing_up"]},
            "conductor_thermal": p5["thermal"],
            "temporal_coordination": p5["coordination"],
        },
        "p7": {
            "snapshot_verification": verification,
            "snapshot_sha256": snapshot["hash"]["value"],
            "report": report,
            "engineering_preview_gate": p7d,
        },
        "outputs": {key: str(value) for key, value in paths.items()},
        "pilot_findings": [
            "El caso usa datos sintéticos; P2/Z0/P5 deben sustituirse por documentación aprobada en el piloto real.",
            "La descripción visual del conductor P2 debe preservar la identidad canónica para no invalidar trazabilidad P3.",
            "P3 usa condición base de catálogo confirmada explícitamente; no crea lookup normativo profesional automático.",
            "Las TCC son TEST_DATA sintéticas; no existe claim de fabricante ni selectividad integral.",
            "El chequeo térmico usa sección y k explícitos que deben validarse en el proyecto real.",
            "IEEE 1584 permanece DEFERRED.",
        ],
        "professional_report": False,
        "professional_emission": False,
    }
    _write_json(paths["summary"], result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="P8A synthetic MT/LV substation pilot")
    parser.add_argument("--output-dir", default="salida_p8a_substation")
    args = parser.parse_args()
    result = run(args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    if not result["ok"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
