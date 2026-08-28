from mcp_electrico import iec60909_benchmarks, p4_completion


def test_p4c09a_reference_is_independent_and_declares_equations():
    basis = iec60909_benchmarks.REFERENCE_BASIS

    assert basis["depends_on_pandapower"] is False
    assert basis["depends_on_opendss"] is False
    assert "|ZQ| = c * Un^2 / Ssc" in basis["equations"]
    assert "R/X = 1 / (X/R)" in basis["equations"]
    assert "22.9 kV" in basis["voltage_factor_scope"]
    assert "20 °C" in basis["line_minimum_temperature"]


def test_p4c09a_reference_values_are_stable_and_physical():
    maximum = iec60909_benchmarks.solve_reference("max")
    minimum = iec60909_benchmarks.solve_reference("min")

    assert maximum["r_x_source"] == 0.1
    assert minimum["r_x_source"] == 0.2
    assert maximum["ikss_ka"] > minimum["ikss_ka"] > 0
    assert maximum["skss_mva"] > minimum["skss_mva"] > 0
    assert maximum["rk_ohm"] > 0 and maximum["xk_ohm"] > 0
    assert minimum["rk_ohm"] > 0 and minimum["xk_ohm"] > 0


def test_p4c09a_suite_matches_pandapower_p4b_with_declared_tolerances():
    suite = iec60909_benchmarks.run_suite()

    assert suite["schema"] == "MCP_ELECTRICO_P4_3PH_BENCHMARK_V1"
    assert suite["pass"] is True
    assert suite["coverage"] == {"three_phase_max": True, "three_phase_min": True}
    # P4C09A sigue siendo solo la evidencia 3F; no se reetiqueta retroactivamente
    # como benchmark global aunque P4C09 global se cierre con P4C06/P4C07/P4C08.
    assert suite["p4c09_complete"] is False
    assert suite["professional_emission"] is False
    assert len(suite["cases"]) == 2
    for case in suite["cases"]:
        assert case["pass"] is True
        assert case["comparison"]["pass"] is True
        assert all(metric["pass"] for metric in case["comparison"]["metrics"].values())


def test_p4c09_global_gate_closes_only_after_all_declared_scope_evidence_exists():
    gate = p4_completion.evaluar_cierre_p4()
    criteria = {item["id"]: item for item in gate["criteria"]}

    assert criteria["P4C01"]["status"] == "DONE"
    assert criteria["P4C02"]["status"] == "DONE"
    assert criteria["P4C03"]["status"] == "DONE"
    assert criteria["P4C04"]["status"] == "DONE"
    assert criteria["P4C09"]["status"] == "DONE"
    assert "3F=P4C09A PASS" in criteria["P4C09"]["evidence"]
    assert "2F=P4C06 PASS" in criteria["P4C09"]["evidence"]
    assert "1F-T=P4C07 PASS" in criteria["P4C09"]["evidence"]
    assert criteria["P4C10"]["status"] == "DONE"
    assert criteria["P4C12"]["status"] == "PENDING"
    assert gate["phase_status"] == "NOT_READY"
