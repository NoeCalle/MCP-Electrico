from __future__ import annotations

import json
from pathlib import Path

from mcp_electrico import (
    real_controlled_execution,
    real_integrated_readiness,
    real_model_materializer,
    real_pilot_intake,
    real_protection_execution,
)


EXPECTED_RELEASE_SHA = "5228e358cf0716dc963f109a15b9e1a2d309f635"
EXPECTED_P9_SHA = "6720da9183c45df299a584430fddea28f4060d7a"
EXPECTED_SCOPES = [
    "AMPACITY",
    "IEC60909_1PH_GROUND_MAX_MIN",
    "IEC60909_3PH_MAX_MIN",
    "POWER_FLOW",
    "PROTECTION_TCC",
    "VOLTAGE_DROP",
]


def _release() -> dict:
    path = (
        Path(__file__).resolve().parents[1]
        / "releases"
        / "mcp_electrico_0_9_reference_validated.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def test_p11a_release_manifest_points_to_exact_known_good_commits():
    release = _release()

    assert release["schema"] == "MCP_ELECTRICO_RELEASE_MANIFEST_V1"
    assert release["release_id"] == "MCP_ELECTRICO_0_9_REFERENCE_VALIDATED"
    assert release["commit_sha"] == EXPECTED_RELEASE_SHA
    assert release["recovery_branch"] == "stable/0.9-reference-validated"

    previous = release["previous_recovery_point"]
    assert previous["commit_sha"] == EXPECTED_P9_SHA
    assert previous["recovery_branch"] == "stable/0.9-engineering-preview"

    assert release["validation"]["p10"] == "CLOSED"
    assert release["validation"]["reference_validation"] == "PASSED"
    assert release["validation"]["reference_project"] == "MCP-REF-SUB-01"
    assert release["validation"]["p10_prs"] == [110, 111, 112, 113, 114, 115, 116]


def test_p11a_release_contract_matches_live_core_schemas_and_scope():
    release = _release()

    assert release["allowed_scope"] == EXPECTED_SCOPES
    assert sorted(real_pilot_intake.ALLOWED_SCOPE) == EXPECTED_SCOPES

    schemas = release["contract_schemas"]
    assert real_pilot_intake.SCHEMA == schemas["p8b_intake"]
    assert real_model_materializer.SCHEMA == schemas["p8c3_materializer"]
    assert real_integrated_readiness.SCHEMA == schemas["p8c5_readiness"]
    assert real_controlled_execution.SCHEMA == schemas["p8d1_execution"]
    assert real_protection_execution.SCHEMA == schemas["p8d2_protection"]


def test_p11a_fail_closed_and_non_professional_policy_is_still_active():
    release = _release()
    safety = release["safety_invariants"]

    assert safety == {
        "automatic_defaults": False,
        "automatic_dispatch": False,
        "automatic_fault_binding": False,
        "crosscheck": False,
        "automatic_normative_lookup": False,
        "professional_report": False,
        "professional_emission": False,
    }

    contract = real_pilot_intake.obtener_contrato_p8b()
    assert contract["automatic_defaults"] is False
    assert contract["automatic_dispatch"] is False
    assert contract["crosscheck"] is False
    assert contract["professional_emission"] is False

    assert release["deferred_or_excluded"]["p6_ieee1584"] == "DEFERRED"
    assert release["deferred_or_excluded"]["independent_mirror_repository"] == "PLANNED_NOT_YET_CREATED"
