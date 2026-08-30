from __future__ import annotations

import inspect

from mcp_electrico import (
    professional_tools,
    real_pilot_intake_tools,
    real_project_dossier_tools,
)


class FakeMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(fn):
            assert fn.__name__ not in self.tools
            self.tools[fn.__name__] = fn
            return fn
        return decorator


def test_p8f1_contract_keeps_all_automatic_behaviour_closed():
    contract = real_project_dossier_tools.obtener_contrato_p8f1()

    assert contract["schema"] == "MCP_ELECTRICO_P8F1_REAL_PILOT_MCP_ENTRYPOINT_V1"
    assert contract["entrypoint"] == "generar_dossier_piloto_real"
    assert contract["orchestrator_schema"] == "MCP_ELECTRICO_P8E2_REAL_PROJECT_DOSSIER_V1"
    assert contract["success_status"] == "DOSSIER_READY_ENGINEERING_PREVIEW"
    assert contract["integrity_required_before_success"] is True
    assert contract["integrity_schema"] == "MCP_ELECTRICO_P8F2_DOSSIER_INTEGRITY_V1"
    assert contract["integrity_verifier"] == "verificar_integridad_dossier_real"
    assert contract["automatic_defaults"] is False
    assert contract["automatic_dispatch"] is False
    assert contract["automatic_fault_binding"] is False
    assert contract["crosscheck"] is False
    assert contract["professional_emission"] is False


def test_p8_registry_exposes_admission_contract_and_integral_dossier(monkeypatch):
    mcp = FakeMCP()
    real_pilot_intake_tools.register(mcp)

    assert "obtener_contrato_p8b_admision_real" in mcp.tools
    assert "evaluar_admision_piloto_real" in mcp.tools
    assert "obtener_contrato_p8f1_piloto_real" in mcp.tools
    assert "obtener_contrato_p8f2_integridad_dossier" in mcp.tools
    assert "generar_dossier_piloto_real" in mcp.tools
    assert "verificar_integridad_dossier_real" in mcp.tools

    calls = []

    def fake_generate(manifest, directorio_salida="mcp_electrico_real_dossier"):
        calls.append((manifest, directorio_salida))
        return {
            "schema": "MCP_ELECTRICO_P8E2_REAL_PROJECT_DOSSIER_V1",
            "status": "BLOCKED_BY_P8D2_EXECUTION",
            "professional_emission": False,
        }

    monkeypatch.setattr(
        real_project_dossier_tools.real_project_dossier,
        "generar_dossier",
        fake_generate,
    )
    manifest = {"project": {"id": "REAL-PILOT-TEST"}}
    result = mcp.tools["generar_dossier_piloto_real"](
        manifest,
        directorio_salida="pilot-output",
    )

    assert calls == [(manifest, "pilot-output")]
    assert result["status"] == "BLOCKED_BY_P8D2_EXECUTION"
    assert result["professional_emission"] is False


def test_professional_registry_reaches_p8f1_entrypoint_and_p8f2_verifier():
    mcp = FakeMCP()
    professional_tools.register(mcp)

    assert "generar_dossier_piloto_real" in mcp.tools
    assert "obtener_contrato_p8f1_piloto_real" in mcp.tools
    assert "obtener_contrato_p8f2_integridad_dossier" in mcp.tools
    assert "verificar_integridad_dossier_real" in mcp.tools


def test_p8f1_registry_has_no_direct_engine_or_study_calculation_route():
    source = inspect.getsource(real_project_dossier_tools)

    forbidden = (
        "opendssdirect",
        "pandapower",
        "calc_sc",
        "analizar_flujo_operacion",
        "evaluar_capacidad_corte",
        "evaluar_tiempo_despeje",
    )
    for token in forbidden:
        assert token not in source

    assert "real_project_dossier.generar_dossier" in source
