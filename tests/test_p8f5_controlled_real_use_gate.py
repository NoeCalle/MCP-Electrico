from __future__ import annotations

import inspect

from mcp_electrico import p8_completion, p8_completion_tools, real_pilot_intake_tools


class FakeMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(fn):
            assert fn.__name__ not in self.tools
            self.tools[fn.__name__] = fn
            return fn
        return decorator


def test_p8f5_gate_closes_p8_for_controlled_real_project_engineering_preview():
    result = p8_completion.evaluar_cierre_p8()

    assert result["schema"] == "MCP_ELECTRICO_P8F5_CONTROLLED_REAL_USE_GATE_V1"
    assert result["phase"] == "P8"
    assert result["phase_status"] == "READY_FOR_CONTROLLED_REAL_PROJECT_USE"
    assert result["p8_closed"] is True
    assert result["controlled_real_project_use_ready"] is True
    assert result["engineering_preview_ready"] is True
    assert result["product_release"] == "MCP_ELECTRICO_0_9_ENGINEERING_PREVIEW"
    assert result["allowed_use"] == "CONTROLLED_REAL_PROJECT_ENGINEERING_PREVIEW"
    assert result["public_entrypoint"] == "generar_dossier_piloto_real"
    assert result["recommended_preflight"] == "evaluar_admision_piloto_real"
    assert result["post_delivery_verification"] == "verificar_integridad_dossier_real"
    assert result["pending_criteria"] == []
    assert len(result["criteria"]) == 9
    assert {item["status"] for item in result["criteria"]} == {"DONE"}
    assert result["next_activity"] == "FIRST_CONTROLLED_REAL_PROJECT"

    assert result["workspace"] == "V5"
    assert result["arc_flash_ieee1584"] == "DEFERRED"
    assert result["iec60909_backend"] == "pandapower_explicit_experimental"
    assert result["iec60909_full_conformance_claim"] is False
    assert result["automatic_defaults"] is False
    assert result["automatic_dispatch"] is False
    assert result["automatic_fault_binding"] is False
    assert result["crosscheck"] is False
    assert result["professional_report"] is False
    assert result["professional_emission"] is False


def test_p8f5_checklist_covers_real_project_evidence_before_execution():
    result = p8_completion.evaluar_cierre_p8()
    checklist = result["required_project_inputs"]

    assert len(checklist) == 10
    assert [item["id"] for item in checklist] == [f"INPUT{i:02d}" for i in range(1, 11)]
    sections = {item["section"] for item in checklist}
    assert {
        "project",
        "source",
        "topology",
        "positive_sequence",
        "zero_sequence_if_1ph_ground",
        "ampacity",
        "protection_devices",
        "tcc",
        "fault_bindings",
        "study_inputs",
    } == sections
    assert result["example_manifest"] == "examples/p8_first_use_manifest.json"
    assert result["example_is_project_evidence"] is False
    ground = next(item for item in checklist if item["section"] == "zero_sequence_if_1ph_ground")
    assert ground["conditional_on"] == "IEC60909_1PH_GROUND_MAX_MIN requested"
    binding = next(item for item in checklist if item["section"] == "fault_bindings")
    assert "current_quantity=ikss_ka" in binding["required"]


def test_p8f5_tools_are_exposed_through_same_public_p8_registry():
    mcp = FakeMCP()
    real_pilot_intake_tools.register(mcp)

    expected = {
        "evaluar_admision_piloto_real",
        "generar_dossier_piloto_real",
        "verificar_integridad_dossier_real",
        "evaluar_cierre_p8f5_uso_real_controlado",
        "obtener_checklist_p8f5_datos_proyecto_real",
    }
    assert expected <= set(mcp.tools)

    gate = mcp.tools["evaluar_cierre_p8f5_uso_real_controlado"]()
    assert gate["controlled_real_project_use_ready"] is True
    assert gate["professional_emission"] is False

    checklist = mcp.tools["obtener_checklist_p8f5_datos_proyecto_real"]()
    assert checklist["schema"] == "MCP_ELECTRICO_P8F5_REAL_PROJECT_INPUT_CHECKLIST_V1"
    assert len(checklist["items"]) == 10
    assert checklist["example_is_project_evidence"] is False
    assert checklist["automatic_defaults"] is False
    assert checklist["professional_emission"] is False


def test_p8f5_gate_is_read_only_and_has_no_direct_engineering_execution_route():
    source = inspect.getsource(p8_completion)
    tools_source = inspect.getsource(p8_completion_tools)

    forbidden = (
        "opendssdirect",
        "pandapower.shortcircuit",
        "calc_sc(",
        "analizar_flujo_operacion(",
        "ejecutar_protecciones(",
        "generar_dossier(",
        "evaluar_capacidad_corte(",
    )
    for token in forbidden:
        assert token not in source
        assert token not in tools_source

    assert "evaluar_cierre_p7" in source
    assert "obtener_contrato_p8f4" in source
    assert "obtener_capacidades_motores" in source


def test_p8f5_fails_closed_if_a_core_p8_contract_reopens_automatic_dispatch(monkeypatch):
    original = p8_completion.real_project_dossier_tools.obtener_contrato_p8f1

    def unsafe_contract():
        value = original()
        value["automatic_dispatch"] = True
        return value

    monkeypatch.setattr(p8_completion.real_project_dossier_tools, "obtener_contrato_p8f1", unsafe_contract)
    result = p8_completion.evaluar_cierre_p8()

    assert result["phase_status"] == "NOT_READY_FOR_CONTROLLED_REAL_PROJECT_USE"
    assert result["p8_closed"] is False
    assert result["controlled_real_project_use_ready"] is False
    assert result["product_release"] is None
    assert result["allowed_use"] is None
    assert result["next_activity"] == "CLOSE_P8F5_PENDING_CRITERIA"
    assert any(item["id"] == "P8F5-03" for item in result["pending_criteria"])
    assert result["professional_emission"] is False
