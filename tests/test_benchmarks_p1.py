from mcp_electrico import benchmarks


def test_reference_solver_returns_physical_results():
    case = dict(benchmarks.BENCHMARK_CASES[0])
    result = benchmarks.solve_balanced_two_bus_reference(case)

    assert 0 < result["vpu_receiving"] < 1
    assert result["current_a"] > 0
    assert result["loss_kw"] > 0
    assert result["loss_kvar"] > 0
    assert result["drop_pct"] > 0


def test_reference_drop_increases_with_line_length():
    base = dict(benchmarks.BENCHMARK_CASES[0])
    longer = dict(base)
    longer["length_km"] = base["length_km"] * 2

    short_result = benchmarks.solve_balanced_two_bus_reference(base)
    long_result = benchmarks.solve_balanced_two_bus_reference(longer)

    assert long_result["drop_pct"] > short_result["drop_pct"]
    assert long_result["loss_kw"] > short_result["loss_kw"]


def test_tolerances_are_declared_and_nonzero():
    required = {
        "vpu_abs",
        "current_a_abs",
        "current_rel_pct",
        "loss_kw_abs",
        "loss_kvar_abs",
        "drop_pct_abs",
    }
    assert required <= set(benchmarks.TOLERANCES)
    assert all(benchmarks.TOLERANCES[key] > 0 for key in required)


def test_each_p1_case_passes_against_independent_reference():
    for case in benchmarks.BENCHMARK_CASES:
        result = benchmarks.run_case(case)
        assert result["pass"], result
        assert set(result["comparisons"]) == {
            "vpu_receiving",
            "current_a",
            "loss_kw",
            "loss_kvar",
            "drop_pct",
        }
        for metric in result["comparisons"].values():
            assert "abs_error" in metric
            assert "rel_error_pct" in metric
            assert metric["pass"] is True


def test_full_p1_suite_reports_no_failures():
    report = benchmarks.run_p1_benchmarks()
    assert report["summary"]["pass"] is True
    assert report["summary"]["failed"] == 0
    assert report["summary"]["passed"] == len(benchmarks.BENCHMARK_CASES)
    assert report["scope"] == "radial_balanced_three_phase_two_bus_constant_pq"
