from copy import deepcopy

from mcp_electrico import engine_selection, p7_completion


def test_p7d_gate_releases_engineering_preview_with_professional_boundary_closed():
    result = p7_completion.evaluar_cierre_p7()

    assert result["schema"] == "MCP_ELECTRICO_P7D_ENGINEERING_PREVIEW_GATE_V1"
    assert result["phase_status"] == "READY_WITH_LIMITATIONS"
    assert result["pending_criteria"] == []
    assert result["ready_for_release"] is True
    assert result["product_release"] == "MCP_ELECTRICO_0_9_ENGINEERING_PREVIEW"
    assert result["engineering_preview_ready"] is True
    assert result["internal_use_ready"] is True
    assert result["allowed_use"] == "CONTROLLED_INTERNAL_ENGINEERING_PREVIEW"
    assert result["next_activity"] == "REAL_SUBSTATION_PILOT"
    assert result["arc_flash_ieee1584"] == "DEFERRED"
    assert result["professional_report"] is False
    assert result["professional_emission"] is False
    assert all(item["status"] == "DONE" for item in result["criteria"])


def test_engine_selection_reflects_completed_p5_without_professional_promotion():
    capabilities = engine_selection.obtener_capacidades_motores()
    protection = capabilities["studies"]["protection_coordination"]
    arc_flash = capabilities["studies"]["arc_flash_ieee1584"]

    assert capabilities["automatic_dispatch"] is False
    assert capabilities["crosscheck"] is False
    assert capabilities["default_engine"] == "opendss"
    assert protection["implemented"] is True
    assert protection["preferred"] == "mcp+pandapower"
    assert protection["professional_emission_candidate"] is False
    assert arc_flash["implemented"] is False
    assert arc_flash["professional_emission_candidate"] is False


def test_p7d_blocks_if_protection_capability_regresses(monkeypatch):
    original = engine_selection.obtener_capacidades_motores

    def regressed():
        value = deepcopy(original())
        value["studies"]["protection_coordination"]["implemented"] = False
        return value

    monkeypatch.setattr(engine_selection, "obtener_capacidades_motores", regressed)
    result = p7_completion.evaluar_cierre_p7()

    assert result["ready_for_release"] is False
    assert result["engineering_preview_ready"] is False
    assert result["product_release"] is None
    pending = {item["id"] for item in result["pending_criteria"]}
    assert "P7D06" in pending
    assert result["professional_emission"] is False


def test_p7d_blocks_if_arc_flash_is_silently_enabled(monkeypatch):
    original = engine_selection.obtener_capacidades_motores

    def arc_flash_enabled():
        value = deepcopy(original())
        value["studies"]["arc_flash_ieee1584"]["implemented"] = True
        return value

    monkeypatch.setattr(engine_selection, "obtener_capacidades_motores", arc_flash_enabled)
    result = p7_completion.evaluar_cierre_p7()

    assert result["ready_for_release"] is False
    assert result["engineering_preview_ready"] is False
    pending = {item["id"] for item in result["pending_criteria"]}
    assert "P7D07" in pending
    assert result["arc_flash_ieee1584"] == "DEFERRED"
    assert result["professional_emission"] is False
