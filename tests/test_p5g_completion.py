import json
import subprocess
import sys

from mcp_electrico import p5_benchmarks, p5_completion, p5_completion_tools


EXPECTED_IDS = [
    "P5G_B01_TCC_BAND_LOGLOG",
    "P5G_B02_TCC_NO_EXTRAPOLATION",
    "P5G_B03_CLEARING_TIME_BAND",
    "P5G_B04_TEMPORAL_COORDINATION",
    "P5G_B05_BREAKING_CAPACITY",
    "P5G_B06_CONDUCTOR_THERMAL",
]


def test_p5g_gate_ready_with_limitations_without_promoting_modules():
    gate = p5_completion.evaluar_cierre_p5()

    assert gate["phase"] == "P5"
    assert gate["phase_version"] == "P5-v1"
    assert gate["phase_status"] == "READY_WITH_LIMITATIONS"
    assert gate["pending_criteria"] == []
    assert all(item["status"] == "DONE" for item in gate["criteria"])
    assert gate["ready_for_next_phase"] is True
    assert gate["next_phase"] == "P7_REPRODUCIBLE_DOSSIER_MINIMUM"
    assert gate["deferred_phase"] == "P6_IEEE1584_ARC_FLASH"
    assert gate["operational_path_ready"] is True
    assert gate["engineering_preview_ready"] is False
    assert gate["engineering_preview_blockers"] == ["P7_REPRODUCIBLE_DOSSIER_MINIMUM"]
    assert gate["professional_emission"] is False

    # P5G cierra la fase funcional; no falsifica una promoción de madurez.
    assert set(gate["module_maturity"]) == {
        "protection_data",
        "tcc_curve_evaluation",
        "protection_checks",
        "protection_clearing_time",
        "protection_coordination",
    }
    assert all(
        item["status"] == "EXPERIMENTAL"
        for item in gate["module_maturity"].values()
    )


def test_p5g_benchmark_contract_is_explicit_and_complete():
    assert p5_benchmarks.SUITE_ID == "MCP_ELECTRICO_P5G_BENCHMARK_SUITE_V1"
    assert list(p5_benchmarks.BENCHMARK_IDS) == EXPECTED_IDS

    gate = p5_completion.evaluar_cierre_p5()
    evidence = gate["benchmark_evidence"]
    assert evidence["suite_id"] == p5_benchmarks.SUITE_ID
    assert evidence["required_benchmark_ids"] == EXPECTED_IDS
    assert evidence["execution_gate"] == "CI_REQUIRED"
    assert evidence["automatic_runtime_execution"] is False


def test_p5g_benchmark_runner_passes_reproducibly_in_subprocess(tmp_path):
    output = tmp_path / "benchmark_p5g.json"
    completed = subprocess.run(
        [
            sys.executable,
            "examples/run_benchmarks_p5g.py",
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    report = json.loads(output.read_text(encoding="utf-8"))

    assert report["pass"] is True
    assert report["failed"] == 0
    assert report["passed"] == 6
    assert report["benchmark_ids"] == EXPECTED_IDS
    assert [item["id"] for item in report["benchmarks"]] == EXPECTED_IDS
    assert all(item["pass"] is True for item in report["benchmarks"])
    assert report["case"]["curve_source_type"] == "TEST_DATA"
    assert report["case"]["manufacturer_claim"] is False
    assert report["case"]["normative_compliance_claim"] is False
    assert report["professional_emission"] is False


def test_p5g_public_tool_is_separate_from_coordination_engine():
    class FakeMCP:
        def __init__(self):
            self.names = []

        def tool(self):
            def decorator(func):
                self.names.append(func.__name__)
                return func
            return decorator

    fake = FakeMCP()
    p5_completion_tools.register(fake)
    assert fake.names == ["evaluar_cierre_p5"]
