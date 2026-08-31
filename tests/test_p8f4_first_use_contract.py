from __future__ import annotations

import json
from pathlib import Path

from mcp_electrico import real_pilot_intake, real_project_dossier_tools


ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "examples" / "p8_first_use_manifest.json"


def test_p8f4_example_manifest_is_explicit_example_and_passes_p8b_admission():
    manifest = json.loads(EXAMPLE.read_text(encoding="utf-8"))

    assert manifest["project"]["id"] == "P8F4-FIRST-USE-001"
    assert "EJEMPLO" in manifest["project"]["source_reference"]
    assert set(manifest["requested_scope"]) == {
        "POWER_FLOW",
        "VOLTAGE_DROP",
        "AMPACITY",
        "IEC60909_3PH_MAX_MIN",
        "IEC60909_1PH_GROUND_MAX_MIN",
        "PROTECTION_TCC",
    }

    result = real_pilot_intake.evaluar_admision(manifest)
    assert result["intake_status"] == "READY_TO_BUILD_MODEL"
    assert result["ready_to_build_model"] is True
    assert result["issue_count"] == 0
    assert result["electrical_calculation_performed"] is False
    assert result["automatic_defaults"] is False
    assert result["automatic_dispatch"] is False
    assert result["crosscheck"] is False
    assert result["professional_emission"] is False


def test_p8f4_contract_exposes_public_sequence_and_fail_closed_repairs():
    contract = real_project_dossier_tools.obtener_contrato_p8f4()

    assert contract["schema"] == "MCP_ELECTRICO_P8F4_FIRST_USE_OPERATIONAL_CONTRACT_V1"
    assert contract["example_manifest"] == "examples/p8_first_use_manifest.json"
    assert contract["example_is_project_data"] is False
    assert contract["example_requires_replacement_with_project_sources"] is True
    assert contract["transport_smoke"] == "MCP_STDIO_SERVER_PY"

    sequence = contract["recommended_sequence"]
    assert [item["tool"] for item in sequence] == [
        "evaluar_admision_piloto_real",
        "generar_dossier_piloto_real",
        "verificar_integridad_dossier_real",
    ]
    assert [item["success_status"] for item in sequence] == [
        "READY_TO_BUILD_MODEL",
        "DOSSIER_READY_ENGINEERING_PREVIEW",
        "DOSSIER_INTEGRITY_VERIFIED",
    ]

    failures = contract["failure_contract"]
    assert failures["admission"]["status"] == "BLOCKED_MISSING_INPUTS"
    assert failures["admission"]["delivery_created"] is False
    assert failures["execution"]["status"] == "BLOCKED_BY_P8D2_EXECUTION"
    assert failures["execution"]["delivery_created"] is False
    assert failures["artifact_generation"]["status"] == "DOSSIER_ARTIFACT_GENERATION_FAILED"
    assert failures["artifact_generation"]["delivery_is_usable"] is False
    assert failures["integrity"]["status"] == "DOSSIER_INTEGRITY_MISMATCH"
    assert failures["integrity"]["delivery_is_usable"] is False

    assert contract["automatic_repair"] is False
    assert contract["automatic_retry"] is False
    assert contract["automatic_defaults"] is False
    assert contract["automatic_dispatch"] is False
    assert contract["automatic_fault_binding"] is False
    assert contract["crosscheck"] is False
    assert contract["professional_emission"] is False


def test_p8f4_contract_tool_is_registered_in_same_public_registry():
    class FakeMCP:
        def __init__(self):
            self.tools = {}

        def tool(self):
            def decorator(fn):
                self.tools[fn.__name__] = fn
                return fn
            return decorator

    mcp = FakeMCP()
    real_project_dossier_tools.register(mcp)

    assert "obtener_contrato_p8f4_primer_uso" in mcp.tools
    assert "generar_dossier_piloto_real" in mcp.tools
    assert "verificar_integridad_dossier_real" in mcp.tools
    result = mcp.tools["obtener_contrato_p8f4_primer_uso"]()
    assert result["schema"] == "MCP_ELECTRICO_P8F4_FIRST_USE_OPERATIONAL_CONTRACT_V1"
    assert result["professional_emission"] is False
