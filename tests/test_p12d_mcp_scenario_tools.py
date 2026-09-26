from __future__ import annotations

import inspect

from mcp_electrico import operating_scenario_tools, professional_tools


class FakeMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(fn):
            assert fn.__name__ not in self.tools
            self.tools[fn.__name__] = fn
            return fn
        return decorator


def test_p12d_contract_keeps_automatic_behavior_closed():
    contract = operating_scenario_tools.obtener_contrato_p12d()

    assert contract["schema"] == "MCP_ELECTRICO_P12D_MCP_SCENARIO_ENTRYPOINT_V1"
    assert contract["tools"] == [
        "obtener_contrato_p12_escenarios_operativos",
        "validar_escenarios_operativos",
        "ejecutar_escenarios_operativos",
    ]
    engine = contract["engine_contract"]
    assert engine["schema"] == "MCP_ELECTRICO_P12_OPERATING_SCENARIOS_V1"
    assert "OPEN_ELEMENT" in engine["allowed_actions"]
    assert "DISABLE_LOAD" in engine["allowed_actions"]
    assert engine["industry_policy"].startswith("INDUSTRY_AGNOSTIC_CORE")
    assert contract["automatic_contingency_selection"] is False
    assert contract["automatic_switching"] is False
    assert contract["automatic_load_shedding"] is False
    assert contract["automatic_retry"] is False
    assert contract["crosscheck"] is False
    assert contract["professional_emission"] is False


def test_p12d_registry_exposes_validation_and_execution(monkeypatch):
    mcp = FakeMCP()
    operating_scenario_tools.register(mcp)

    assert set(mcp.tools) == {
        "obtener_contrato_p12_escenarios_operativos",
        "validar_escenarios_operativos",
        "ejecutar_escenarios_operativos",
    }

    calls = []

    def fake_validate(manifest, package):
        calls.append(("validate", manifest, package))
        return {"validation_status": "READY_FOR_SCENARIO_EXECUTION"}

    def fake_execute(manifest, package):
        calls.append(("execute", manifest, package))
        return {
            "execution_status": "SCENARIO_SET_EXECUTION_COMPLETED",
            "professional_emission": False,
        }

    monkeypatch.setattr(operating_scenario_tools.operating_scenarios, "validar_paquete", fake_validate)
    monkeypatch.setattr(operating_scenario_tools.operating_scenarios, "ejecutar_paquete", fake_execute)

    manifest = {"project": {"id": "TEST"}}
    package = {"project_id": "TEST", "scenarios": []}

    validation = mcp.tools["validar_escenarios_operativos"](manifest, package)
    execution = mcp.tools["ejecutar_escenarios_operativos"](manifest, package)

    assert validation["validation_status"] == "READY_FOR_SCENARIO_EXECUTION"
    assert execution["execution_status"] == "SCENARIO_SET_EXECUTION_COMPLETED"
    assert execution["professional_emission"] is False
    assert calls == [
        ("validate", manifest, package),
        ("execute", manifest, package),
    ]


def test_professional_registry_reaches_p12d_tools():
    mcp = FakeMCP()
    professional_tools.register(mcp)

    assert "obtener_contrato_p12_escenarios_operativos" in mcp.tools
    assert "validar_escenarios_operativos" in mcp.tools
    assert "ejecutar_escenarios_operativos" in mcp.tools


def test_p12d_tool_wrapper_does_not_embed_an_electrical_engine():
    source = inspect.getsource(operating_scenario_tools)

    forbidden = (
        "opendssdirect",
        "pandapower",
        "calc_sc",
        "Solve",
        "Open ",
        "Close ",
    )
    for token in forbidden:
        assert token not in source

    assert "operating_scenarios.validar_paquete" in source
    assert "operating_scenarios.ejecutar_paquete" in source
