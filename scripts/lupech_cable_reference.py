"""Q12B published real-design facts and high-precision acceptance oracle.

No production imports, network model, normative lookup or inferred trip time.
"""
from decimal import Decimal, localcontext
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FACTS = ROOT / "examples/qualification/lupech_cables_2023.json"


def load_facts():
    return json.loads(FACTS.read_text(encoding="utf8"))


def reference(facts, row):
    """Use dimensional Decimal arithmetic; no MCP result feeds this oracle."""
    with localcontext() as ctx:
        ctx.prec = 40
        current = Decimal(str(row["fault_ka"])) * 1000
        duration = Decimal(str(row["duration_s"]))
        section = Decimal(str(row["section_mm2"]))
        k = Decimal(str(facts["k_a_sqrt_s_per_mm2"]))
        minimum = current * duration.sqrt() / k
        demand = current ** 2 * duration
        capacity = (k * section) ** 2
        return {"minimum_section_mm2":float(minimum),
                "published_minimum_difference_mm2":float(minimum-Decimal(str(row["published_minimum_mm2"]))),
                "status":"PASS" if demand <= capacity else "FAIL",
                "actual_i2t_a2s":float(demand),"limit_k2s2_a2s":float(capacity),
                "utilization_ratio":float(demand/capacity),
                "max_permissible_clearing_time_s_at_input_current":float(capacity/current**2),
                "max_permissible_current_ka_at_input_time":float(k*section/duration.sqrt()/1000)}


def arguments(facts, row):
    src = facts["repository_url"]
    locator = f"{src}; PDF p.{row['page']}, Table {row['table']}, {row['column']}"
    return {"elemento":"Line.lupech_"+row["id"],
            "corriente_falla_ka":row["fault_ka"],"tiempo_despeje_s":row["duration_s"],
            "seccion_mm2":row["section_mm2"],"k_a_sqrt_s_per_mm2":facts["k_a_sqrt_s_per_mm2"],
            "fuente_k":src+"; PDF p.159, Al/XLPE 90 to 250 C, k=94 (explicit published coefficient)",
            "fuente_tiempo":locator+"; published withstand criterion, not measured/curve-derived clearing time",
            "fuente_seccion":locator+"; individual cable, parallel runs not summed"}


def compare(result, expected):
    assert result["status"] == expected["status"], (result,expected)
    assert result["scope"] == "EXPLICIT_K_S_TIME_ADIABATIC_CHECK"
    assert result["section_binding"]["status"] == "EXPLICIT_WITHOUT_LIBRARY_ASSIGNMENT"
    assert not result["full_standard_compliance_claim"] and not result["professional_emission"]
    errors = {k:abs(result["results"][k]-expected[k]) for k in result["results"]}
    # Relative tolerance 1e-12, absolute floor 1e-10, fixed before CI execution.
    passed = all(v <= max(1e-10,abs(expected[k])*1e-12) for k,v in errors.items())
    assert passed, errors
    return {"comparison_passed":passed,"absolute_errors":errors,
            "relative_tolerance":1e-12,"absolute_floor":1e-10}
