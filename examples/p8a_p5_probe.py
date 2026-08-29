"""Probe temporal de diagnóstico P8A; se retirará antes del merge."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from examples import p8a_substation_pilot as pilot
from mcp_electrico import (
    iec60909_suite,
    pandapower_engine,
    protection_clearing_time,
    protection_curves,
    protection_data,
)


out = Path("p8a_probe").resolve()
out.mkdir(parents=True, exist_ok=True)
pilot._build_model(out)
model = pandapower_engine._collect_active_model()
fault = iec60909_suite.ejecutar_3ph_max_min(
    "crit_bus", line_endtemp_degree_c=pilot.TEMPERATURES_MIN
)
max_case = fault["scenarios"]["max"]
ikss_ka = float(max_case["results"]["ikss_ka"])
current_a = ikss_ka * 1000.0
result = {
    "model_buses": model["buses"],
    "fault_max": max_case,
    "ikss_ka": ikss_ka,
    "current_a": current_a,
    "device": protection_data.obtener_dispositivo("QF_CRIT_LV"),
    "readiness": protection_data.evaluar_preparacion("QF_CRIT_LV"),
    "dataset": protection_curves.obtener_dataset("P8A_QF_CRIT_TEST_DATASET"),
    "tcc": protection_curves.evaluar_dispositivo("QF_CRIT_LV", current_a),
    "clearing": protection_clearing_time.evaluar_tiempo_despeje("QF_CRIT_LV", current_a),
}
print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, default=str))
