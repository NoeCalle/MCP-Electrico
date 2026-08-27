from math import sqrt

from mcp_electrico import (
    core,
    iec60909_benchmarks_2ph,
    iec60909_two_phase,
    professional_data,
    visual_state,
)


def _prepare(name="p4c06"):
    core.crear_circuito(name, 22.9)
    visual_state.reset()
    professional_data.reset()
    professional_data.definir_red_equivalente(
        kv_ll=22.9,
        scc_max_mva=500.0,
        x_r_max=10.0,
        scc_min_mva=250.0,
        x_r_min=5.0,
        fuente_referencia="P4C06 test source",
    )
    core.agregar_linea(
        "f1", "sourcebus", "bus1", 0.25, fases=3, r1_ohm_km=0.18, x1_ohm_km=0.09
    )


def test_p4c06_independent_benchmark_passes_max_and_min():
    suite = iec60909_benchmarks_2ph.run_suite()

    assert suite["pass"] is True
    assert suite["p4c06_complete"] is True
    assert suite["p4c09_complete"] is False
    assert suite["reference_basis"]["depends_on_pandapower"] is False
    assert suite["reference_basis"]["depends_on_opendss"] is False
    assert len(suite["cases"]) == 2
    assert all(item["pass"] for item in suite["cases"])


def test_p4c06_reference_ratio_is_sqrt3_over_2_for_z2_equals_z1():
    for case in ("max", "min"):
        reference = iec60909_benchmarks_2ph.solve_reference(case)
        assert abs(reference["ratio_2ph_to_3ph"] - sqrt(3.0) / 2.0) < 1e-12


def test_2ph_min_requires_explicit_line_temperature():
    _prepare("p4c06_min_temp")
    result = iec60909_two_phase.ejecutar_2ph("min", "bus1")

    assert result["ok"] is False
    assert any(item["code"] == "P4SC201" for item in result["issues"])
    assert result["professional_emission"] is False


def test_2ph_duty_requires_explicit_topology_and_time():
    _prepare("p4c06_duty_gate")
    result = iec60909_two_phase.ejecutar_2ph(
        "max", "bus1", calcular_ip_ith=True
    )

    assert result["ok"] is False
    codes = {item["code"] for item in result["issues"]}
    assert "P4SC301" in codes
    assert "P4SC302" in codes


def test_2ph_executes_with_explicit_scope_and_does_not_promote_skss():
    _prepare("p4c06_execute")
    result = iec60909_two_phase.ejecutar_2ph(
        "max",
        "bus1",
        calcular_ip_ith=True,
        topology="radial",
        tk_s=0.2,
        kappa_method="C",
    )

    assert result["ok"] is True
    assert result["fault"] == "2ph"
    assert result["results"]["ikss_ka"] > 0
    assert result["results"]["ip_ka"] > result["results"]["ikss_ka"]
    assert result["results"]["ith_ka"] > 0
    assert "skss_mva" not in result["results"]
    assert result["negative_sequence_policy"]["z2_relation"] == "Z2 = Z1"
    assert result["negative_sequence_policy"]["universal_assumption"] is False
    assert result["professional_emission"] is False


def test_2ph_ip_is_time_independent_and_ith_changes_with_tk():
    _prepare("p4c06_time")
    short = iec60909_two_phase.ejecutar_2ph(
        "max", "bus1", calcular_ip_ith=True, topology="radial", tk_s=0.1
    )
    long = iec60909_two_phase.ejecutar_2ph(
        "max", "bus1", calcular_ip_ith=True, topology="radial", tk_s=1.0
    )

    assert short["ok"] is True and long["ok"] is True
    assert abs(short["results"]["ip_ka"] - long["results"]["ip_ka"]) < 1e-12
    assert abs(short["results"]["ith_ka"] - long["results"]["ith_ka"]) > 1e-6
