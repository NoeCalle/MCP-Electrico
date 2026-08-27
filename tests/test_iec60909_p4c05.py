import pytest

from mcp_electrico import (
    core,
    engine_selection,
    iec60909,
    p4_completion,
    professional_data,
    visual_state,
)


def _source_only():
    core.crear_circuito("p4_duty", 22.9)
    visual_state.reset()
    professional_data.reset()
    professional_data.definir_red_equivalente(
        kv_ll=22.9,
        scc_max_mva=500.0,
        x_r_max=10.0,
        scc_min_mva=250.0,
        x_r_min=5.0,
        fuente_referencia="P4C05 fixture",
    )


def test_p4c05_requires_explicit_topology_and_clearing_time():
    _source_only()

    no_topology = iec60909.ejecutar_3ph(
        "max", "sourcebus", calcular_ip_ith=True, tk_s=0.2
    )
    no_time = iec60909.ejecutar_3ph(
        "max", "sourcebus", calcular_ip_ith=True, topology="radial"
    )
    auto_topology = iec60909.ejecutar_3ph(
        "max", "sourcebus", calcular_ip_ith=True, topology="auto", tk_s=0.2
    )

    assert no_topology["ok"] is False
    assert any(issue["code"] == "P4SC301" for issue in no_topology["issues"])
    assert no_time["ok"] is False
    assert any(issue["code"] == "P4SC302" for issue in no_time["issues"])
    assert auto_topology["ok"] is False
    assert any(issue["code"] == "P4SC301" for issue in auto_topology["issues"])


def test_p4c05_rejects_nonpositive_tk_and_unvalidated_kappa_method():
    _source_only()

    bad_tk = iec60909.ejecutar_3ph(
        "max", "sourcebus", calcular_ip_ith=True,
        topology="radial", tk_s=0.0,
    )
    bad_method = iec60909.ejecutar_3ph(
        "max", "sourcebus", calcular_ip_ith=True,
        topology="radial", tk_s=0.2, kappa_method="B",
    )

    assert bad_tk["ok"] is False
    assert any(issue["code"] == "P4SC302" for issue in bad_tk["issues"])
    assert bad_method["ok"] is False
    assert any(issue["code"] == "P4SC303" for issue in bad_method["issues"])


def test_p4c05_executes_ip_and_ith_with_declared_parameters():
    _source_only()

    result = iec60909.ejecutar_3ph(
        "max",
        "sourcebus",
        calcular_ip_ith=True,
        topology="radial",
        tk_s=0.2,
        kappa_method="C",
    )

    assert result["ok"] is True
    assert result["results"]["ikss_ka"] > 0
    assert result["results"]["ip_ka"] > result["results"]["ikss_ka"]
    assert result["results"]["ith_ka"] > 0
    assert result["input_projection"]["duty"] == {
        "requested": True,
        "topology": "radial",
        "tk_s": 0.2,
        "kappa_method": "C",
    }
    assert result["professional_emission"] is False


def test_p4c05_ith_responds_to_explicit_clearing_time_while_ip_does_not():
    _source_only()
    short = iec60909.ejecutar_3ph(
        "max", "sourcebus", calcular_ip_ith=True,
        topology="radial", tk_s=0.1,
    )
    long = iec60909.ejecutar_3ph(
        "max", "sourcebus", calcular_ip_ith=True,
        topology="radial", tk_s=1.0,
    )

    assert short["ok"] is True and long["ok"] is True
    assert short["results"]["ip_ka"] == pytest.approx(long["results"]["ip_ka"], rel=1e-12)
    assert short["results"]["ith_ka"] != pytest.approx(long["results"]["ith_ka"], rel=1e-9)


def test_p4c05_matrix_e_declares_experimental_pandapower_without_professional_emission():
    matrix = engine_selection.obtener_capacidades_motores()
    capability = matrix["studies"]["iec60909"]

    assert matrix["automatic_dispatch"] is False
    assert matrix["crosscheck"] is False
    assert capability["preferred"] == "pandapower"
    assert capability["implemented"] is True
    assert capability["professional_emission_candidate"] is False
    assert any("topology y tk_s explícitos" in item for item in capability["requirements"])
    assert "experimentalmente" in capability["reason"]


def test_p4c05_gate_remains_done_after_p4c06_without_closing_p4():
    gate = p4_completion.evaluar_cierre_p4()
    criteria = {item["id"]: item for item in gate["criteria"]}
    states = {cid: item["status"] for cid, item in criteria.items()}

    for cid in ("P4C01", "P4C02", "P4C03", "P4C04", "P4C05", "P4C06"):
        assert states[cid] == "DONE"
    for cid in ("P4C07", "P4C08", "P4C09", "P4C10", "P4C11", "P4C12"):
        assert states[cid] == "PENDING"
    assert "Pendiente" not in criteria["P4C05"]["evidence"]
    assert "topology radial|meshed" in criteria["P4C05"]["evidence"]
    assert gate["phase_status"] == "NOT_READY"
    assert gate["professional_emission"] is False
