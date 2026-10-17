"""Independent high-precision manufacturer-example reference, never operating code."""
from decimal import Decimal, localcontext
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FACTS = ROOT / "examples/qualification/abb_total_i2t_2006.json"


def load_facts():
    return json.loads(FACTS.read_text(encoding="utf8"))


def arguments(facts):
    source = facts["energy_point"]["source_reference"]
    return {"dispositivo":"Protection.abb_cb1","elemento":"Bus.sourcebus",
        "corriente_falla_ka":facts["fault_current_ka"],"tension_operacion_kv":facts["voltage_kv"],
        "seccion_mm2":facts["conductor"]["section_mm2"],
        "k_a_sqrt_s_per_mm2":facts["conductor"]["k_a_sqrt_s_per_mm2"],
        "fuente_corriente":source+"; published prospective current, NOT a network solve",
        "fuente_k":source+"; published k=115 in k2S2 calculation",
        "fuente_seccion":source+"; published 50 mm2 Cu/PVC cable",
        "punto_energia":dict(facts["energy_point"])}


def reference():
    with localcontext() as ctx:
        ctx.prec = 40
        # Independent dimensional conversion of ABB's 0.75 (kA)^2 s.
        energy = Decimal("0.75")*Decimal(1000)**2
        capacity = Decimal(115)**2*Decimal(50)**2
        return {"total_let_through_i2t_a2s":float(energy),"limit_k2s2_a2s":float(capacity),
            "utilization_ratio":float(energy/capacity),"minimum_section_mm2":float(energy.sqrt()/115)}


def compare(result):
    expected = reference()
    assert result["status"] == "PASS" and result["thermal_calculation_performed"]
    assert result["breaking_capacity_check"]["status"] == "PASS"
    assert result["clearing_time"] is None and not result["clearing_time_derived_from_i2t"]
    assert not result["full_standard_compliance_claim"] and not result["professional_emission"]
    errors = {k:abs(result["results"][k]-v) for k,v in expected.items()}
    assert all(e <= max(1e-10,abs(expected[k])*1e-12) for k,e in errors.items()),errors
    return {"comparison_passed":True,"absolute_errors":errors,"reference":expected,
        "relative_tolerance":1e-12,"absolute_floor":1e-10}
