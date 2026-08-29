"""P7D — gate final para MCP Eléctrico 0.9 Engineering Preview.

El gate habilita únicamente uso interno controlado. No promociona la madurez de
P1-P7, no afirma conformidad normativa integral y mantiene
``professional_emission=false``.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import (
    engine_selection,
    p5_completion,
    project_report,
    project_reconstruction,
    project_snapshot,
    validation_status,
    workspace_p5_view,
    workspace_v5,
)

SCHEMA = "MCP_ELECTRICO_P7D_ENGINEERING_PREVIEW_GATE_V1"
RELEASE = "MCP_ELECTRICO_0_9_ENGINEERING_PREVIEW"
PHASE_READY = "READY_WITH_LIMITATIONS"
PHASE_NOT_READY = "NOT_READY"
ARC_FLASH_POLICY = "DEFERRED"
ALLOWED_USE = "CONTROLLED_INTERNAL_ENGINEERING_PREVIEW"

_ACCEPTABLE_P7_MATURITY = {
    "EXPERIMENTAL",
    "UNDER_VALIDATION",
    "VALIDATED_WITH_LIMITATIONS",
    "VALIDATED",
}


def _criterion(cid: str, name: str, done: bool, evidence: str, blocker: str) -> dict[str, Any]:
    return {
        "id": cid,
        "name": name,
        "status": "DONE" if done else "PENDING",
        "evidence": evidence,
        "blocking_reason": None if done else blocker,
    }


def _criteria() -> list[dict[str, Any]]:
    p5 = p5_completion.evaluar_cierre_p5()
    matrix = validation_status.get_validation_matrix()
    engines = engine_selection.obtener_capacidades_motores()
    studies = engines.get("studies") or {}
    protection_capability = studies.get("protection_coordination") or {}
    arc_flash_capability = studies.get("arc_flash_ieee1584") or {}
    p7_modules = {
        name: matrix.get(name) or {}
        for name in ("reproducible_project", "project_reconstruction", "technical_report")
    }
    p7_implemented = all(
        item.get("status") in _ACCEPTABLE_P7_MATURITY
        for item in p7_modules.values()
    )
    professional_report = matrix.get("professional_report") or {}
    arc_flash = matrix.get("arc_flash_ieee1584") or {}
    p7c_contract = project_report.obtener_contrato_p7c()

    return [
        _criterion(
            "P7D01",
            "p5_operational_handoff",
            p5.get("phase_status") == "READY_WITH_LIMITATIONS"
            and p5.get("operational_path_ready") is True
            and p5.get("professional_emission") is False,
            "P5G phase_status=READY_WITH_LIMITATIONS + operational_path_ready=true",
            "P5 debe estar cerrado funcionalmente antes de habilitar la Preview.",
        ),
        _criterion(
            "P7D02",
            "p7a_reproducible_snapshot",
            project_snapshot.SCHEMA == "MCP_ELECTRICO_P7A_PROJECT_SNAPSHOT_V1"
            and p7_modules["reproducible_project"].get("status") in _ACCEPTABLE_P7_MATURITY,
            f"{project_snapshot.SCHEMA}; reproducible_project={p7_modules['reproducible_project'].get('status')}",
            "Falta snapshot P7A reproducible o su madurez sigue sin implementar.",
        ),
        _criterion(
            "P7D03",
            "p7b_verified_reconstruction",
            project_reconstruction.SCHEMA == "MCP_ELECTRICO_P7B_RECONSTRUCTION_V1"
            and p7_modules["project_reconstruction"].get("status") in _ACCEPTABLE_P7_MATURITY,
            f"{project_reconstruction.SCHEMA}; project_reconstruction={p7_modules['project_reconstruction'].get('status')}",
            "Falta reconstrucción P7B verificable/fail-closed.",
        ),
        _criterion(
            "P7D04",
            "p7c_technical_report",
            project_report.SCHEMA == "MCP_ELECTRICO_P7C_TECHNICAL_REPORT_V1"
            and p7_modules["technical_report"].get("status") in _ACCEPTABLE_P7_MATURITY
            and p7c_contract.get("source_integrity_required") == "HASH_MATCH"
            and p7c_contract.get("pdf_export_mode") == "BROWSER_PRINT"
            and p7c_contract.get("electrical_recalculation") is False
            and p7c_contract.get("browser_engineering_calculation") is False
            and p7c_contract.get("professional_report") is False,
            f"{project_report.SCHEMA}; technical_report={p7_modules['technical_report'].get('status')}; HASH_MATCH; BROWSER_PRINT",
            "Falta reporte P7C reproducible o su contrato permite recalcular/promover resultados.",
        ),
        _criterion(
            "P7D05",
            "workspace_v5_persistent_visual",
            workspace_p5_view.MARKER == "<!-- MCP-P5-PROTECTION-V5 -->"
            and callable(workspace_v5.enhance_file),
            "Workspace V5 extiende V4; marcador P5 presente; cálculo browser=false por contrato P5F",
            "Falta Workspace V5 persistente o su capa P5 visual.",
        ),
        _criterion(
            "P7D06",
            "deterministic_engine_policy",
            engines.get("automatic_dispatch") is False
            and engines.get("crosscheck") is False
            and engines.get("default_engine") == "opendss"
            and protection_capability.get("implemented") is True
            and protection_capability.get("preferred") == "mcp+pandapower"
            and protection_capability.get("professional_emission_candidate") is False,
            "automatic_dispatch=false; crosscheck=false; default_engine=opendss; P5 coordination implemented sin emisión profesional",
            "La matriz de motores no refleja correctamente la política o capacidad P5 vigente.",
        ),
        _criterion(
            "P7D07",
            "arc_flash_explicitly_deferred",
            ARC_FLASH_POLICY == "DEFERRED"
            and p5.get("deferred_phase") == "P6_IEEE1584_ARC_FLASH"
            and arc_flash.get("status") == "NOT_IMPLEMENTED"
            and arc_flash_capability.get("implemented") is False
            and arc_flash_capability.get("professional_emission_candidate") is False,
            "P6_IEEE1584_ARC_FLASH=DEFERRED; arc_flash_ieee1584=NOT_IMPLEMENTED y no ejecutable",
            "Arc Flash debe permanecer explícitamente diferido para esta release.",
        ),
        _criterion(
            "P7D08",
            "professional_boundary_closed",
            p7_implemented
            and professional_report.get("status") == "NOT_IMPLEMENTED"
            and p5.get("professional_emission") is False
            and p7c_contract.get("professional_emission") is False,
            "P7A/B/C implementados con madurez explícita; professional_report=NOT_IMPLEMENTED; professional_emission=false",
            "La Preview no puede habilitarse si falta P7A/B/C o se abre emisión profesional.",
        ),
    ]


def evaluar_cierre_p7() -> dict[str, Any]:
    """Evalúa si MCP Eléctrico puede declararse Engineering Preview 0.9."""
    criteria = _criteria()
    pending = [deepcopy(item) for item in criteria if item["status"] != "DONE"]
    ready = not pending
    return {
        "schema": SCHEMA,
        "phase": "P7",
        "phase_version": "P7-minimum-operational",
        "phase_status": PHASE_READY if ready else PHASE_NOT_READY,
        "criteria": deepcopy(criteria),
        "pending_criteria": pending,
        "ready_for_release": ready,
        "product_release": RELEASE if ready else None,
        "engineering_preview_ready": ready,
        "internal_use_ready": ready,
        "arc_flash_ieee1584": ARC_FLASH_POLICY,
        "professional_report": False,
        "professional_emission": False,
        "allowed_use": ALLOWED_USE if ready else None,
        "next_activity": "REAL_SUBSTATION_PILOT" if ready else "CLOSE_P7D_PENDING_CRITERIA",
        "note": (
            "Engineering Preview 0.9 habilita uso interno controlado dentro de los alcances y limitaciones declarados. "
            "No significa certificación, conformidad normativa integral ni autorización de emisión profesional."
        ),
    }
