"""P5C: cable withstand using a published total let-through I2t point.

No conversion of prospective current and I2t into a fictional clearing time.
One exact manufacturer point only: no interpolation, extrapolation or backup.
"""
from copy import deepcopy
from math import isclose, isfinite, sqrt

from . import protection_data
from .protection_checks import _positive, _reference, _section_binding, evaluar_capacidad_corte

SCHEMA = "MCP_ELECTRICO_P5C_TOTAL_LET_THROUGH_V1"


def evaluar_energia_pasante_conductor(
    dispositivo: str,
    elemento: str,
    corriente_falla_ka: float,
    tension_operacion_kv: float,
    seccion_mm2: float,
    k_a_sqrt_s_per_mm2: float,
    fuente_corriente: str,
    fuente_k: str,
    fuente_seccion: str,
    punto_energia: dict,
) -> dict:
    """Check an explicitly sourced total I2t and Icu for the same device/point.

    punto_energia requires manufacturer, model, current_ka, voltage_kv,
    value, unit (A2s or kA2s), semantics (TOTAL_LET_THROUGH_I2T), and
    source_reference. Unit conversion is explicit and recorded. A pre-arcing
    or melting integral is insufficient for conductor protection.
    """
    fault = _positive(corriente_falla_ka,"P5C301","corriente_falla_ka")
    voltage = _positive(tension_operacion_kv,"P5C302","tension_operacion_kv")
    section = _positive(seccion_mm2,"P5C303","seccion_mm2")
    k = _positive(k_a_sqrt_s_per_mm2,"P5C304","k_a_sqrt_s_per_mm2")
    fault_source = _reference(fuente_corriente,"P5C305","fuente_corriente")
    k_source = _reference(fuente_k,"P5C306","fuente_k")
    section_source = _reference(fuente_seccion,"P5C307","fuente_seccion")
    if not isinstance(punto_energia,dict):
        raise ValueError("P5C308: punto_energia debe ser un objeto con procedencia y condiciones explicitas.")
    point = deepcopy(punto_energia)
    base = {"schema":SCHEMA,"scope":"EXACT_SOURCED_TOTAL_I2T_AND_DECLARED_BREAKING_CAPACITY",
        "device_id":str(dispositivo),"element":str(elemento),
        "fault":{"current_ka":fault,"voltage_kv":voltage,"source_reference":fault_source},
        "energy_reference":point,"thermal_calculation_performed":False,
        "clearing_time":None,"clearing_time_derived_from_i2t":False,
        "interpolation_used":False,"extrapolated":False,"backup_coordination_claim":False,
        "full_standard_compliance_claim":False,"professional_emission":False}
    if point.get("semantics") != "TOTAL_LET_THROUGH_I2T":
        return {**base,"status":"ENERGY_SEMANTICS_NOT_TOTAL"}
    unit = point.get("unit")
    if unit not in {"A2s","kA2s"}:
        return {**base,"status":"ENERGY_UNIT_NOT_SUPPORTED"}
    energy_source = _reference(point.get("source_reference"),"P5C309","punto_energia.source_reference")
    energy = _positive(point.get("value"),"P5C310","punto_energia.value")
    ref_current = _positive(point.get("current_ka"),"P5C311","punto_energia.current_ka")
    ref_voltage = _positive(point.get("voltage_kv"),"P5C312","punto_energia.voltage_kv")
    if not isclose(fault,ref_current,rel_tol=1e-9,abs_tol=1e-12) or not isclose(voltage,ref_voltage,rel_tol=1e-9,abs_tol=1e-12):
        return {**base,"status":"ENERGY_REFERENCE_POINT_MISMATCH"}
    device = protection_data.obtener_dispositivo(dispositivo)
    if not device:
        return {**base,"status":"DEVICE_NOT_FOUND"}
    if str(elemento).strip().casefold() != device["protected_element"].casefold():
        return {**base,"status":"PROTECTED_ELEMENT_MISMATCH"}
    for key in ("manufacturer","model"):
        actual,declared = str(device.get(key) or "").strip(),str(point.get(key) or "").strip()
        if not actual or not declared:
            return {**base,"status":"DEVICE_IDENTITY_INCOMPLETE"}
        if actual.casefold() != declared.casefold():
            return {**base,"status":"ENERGY_DEVICE_IDENTITY_MISMATCH"}
    if not isclose(float(device.get("ratings",{}).get("ue_kv") or 0),voltage,rel_tol=1e-9,abs_tol=1e-12):
        return {**base,"status":"BREAKING_RATING_VOLTAGE_MISMATCH"}
    binding = _section_binding(str(elemento),section,section_source)
    if binding["status"] == "SECTION_MISMATCH":
        return {**base,"status":"SECTION_MISMATCH","section_binding":binding}
    breaking = evaluar_capacidad_corte(dispositivo,fault,voltage,fault_source)
    if breaking["status"] != "PASS":
        return {**base,"status":"BREAKING_CAPACITY_NOT_PASSED","breaking_capacity_check":breaking}
    multiplier = 1. if unit == "A2s" else 1_000_000.
    demand = energy * multiplier
    scaled_section = k*section
    capacity = scaled_section*scaled_section
    # Every accepted input is finite. Reject overflow rather than emit Infinity.
    if not isfinite(demand) or not isfinite(capacity) or capacity <= 0:
        raise ValueError("P5C313: energia o capacidad fuera del rango numerico finito.")
    passed = demand <= capacity*(1+1e-12)
    utilization,minimum = demand/capacity,sqrt(demand)/k
    if not isfinite(utilization) or not isfinite(minimum):
        raise ValueError("P5C313: resultado fuera del rango numerico finito.")
    return {**base,"status":"PASS" if passed else "FAIL",
        "device_id":device["id"],"element":device["protected_element"],
        "energy_reference_status":"EXACT_PUBLISHED_POINT",
        "energy_source_reference":energy_source,
        "unit_conversion":{"input_unit":unit,"output_unit":"A2s","multiplier":multiplier},
        "section_binding":binding,"breaking_capacity_check":breaking,
        "thermal_calculation_performed":True,
        "inputs":{"section_mm2":section,"k_a_sqrt_s_per_mm2":k,"k_source_reference":k_source,
            "section_source_reference":section_source},
        "results":{"total_let_through_i2t_a2s":demand,"limit_k2s2_a2s":capacity,
            "utilization_ratio":utilization,"minimum_section_mm2":minimum}}
