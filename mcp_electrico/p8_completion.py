"""P8F5 — gate final de uso real controlado para MCP Eléctrico 0.9.

Este gate no ejecuta ingeniería ni amplía la madurez de los módulos. Comprueba
que los contratos P7/P8 mantienen cerradas las fronteras demostradas por el
piloto y habilita únicamente uso de proyectos reales bajo Engineering Preview.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import (
    dossier_integrity,
    engine_selection,
    p7_completion,
    real_pilot_intake,
    real_project_dossier,
    real_project_dossier_tools,
    workspace_p8d2_view,
    workspace_v5,
)

SCHEMA = "MCP_ELECTRICO_P8F5_CONTROLLED_REAL_USE_GATE_V1"
RELEASE = "MCP_ELECTRICO_0_9_ENGINEERING_PREVIEW"
PHASE_READY = "READY_FOR_CONTROLLED_REAL_PROJECT_USE"
PHASE_NOT_READY = "NOT_READY_FOR_CONTROLLED_REAL_PROJECT_USE"
ALLOWED_USE = "CONTROLLED_REAL_PROJECT_ENGINEERING_PREVIEW"
ARC_FLASH_POLICY = "DEFERRED"


def _criterion(cid: str, name: str, done: bool, evidence: str, blocker: str) -> dict[str, Any]:
    return {
        "id": cid,
        "name": name,
        "status": "DONE" if done else "PENDING",
        "evidence": evidence,
        "blocking_reason": None if done else blocker,
    }


def required_project_inputs() -> list[dict[str, Any]]:
    """Checklist mínimo que el usuario debe sustituir por datos/procedencias reales."""
    return [
        {
            "id": "INPUT01",
            "section": "project",
            "required": ["project.id", "project.name", "project.source_reference"],
            "evidence_expected": "Identidad, revisión y referencia del expediente/SLD controlado.",
        },
        {
            "id": "INPUT02",
            "section": "source",
            "required": [
                "source.bus", "source.kv_ll", "source.frequency_hz", "source.scc_max_mva",
                "source.x_r_max", "source.scc_min_mva", "source.x_r_min", "source.source_reference",
            ],
            "evidence_expected": "Estudio o datos de la red aguas arriba para escenarios MAX/MIN.",
        },
        {
            "id": "INPUT03",
            "section": "topology",
            "required": ["topology.buses", "topology.transformers", "topology.lines", "topology.loads"],
            "evidence_expected": "SLD, cuadro de cargas, fichas de transformadores y cuadro/cálculo de cables.",
        },
        {
            "id": "INPUT04",
            "section": "positive_sequence",
            "required": [
                "transformer uk_percent and vector_group",
                "transformer x_r or equivalent supported evidence",
                "line length_km, r1_ohm_km, x1_ohm_km",
            ],
            "evidence_expected": "Parámetros eléctricos trazables; no completar impedancias con defaults silenciosos.",
        },
        {
            "id": "INPUT05",
            "section": "zero_sequence_if_1ph_ground",
            "required": [
                "zero_sequence.source R0/X0 MAX/MIN",
                "zero_sequence.lines R0/X0/C0",
                "zero_sequence.transformers Z0, neutral_side and neutral_mode",
            ],
            "conditional_on": "IEC60909_1PH_GROUND_MAX_MIN requested",
            "evidence_expected": "Estudio/cálculo Z0 y configuración real de neutro; no asumir Z0=Z1.",
        },
        {
            "id": "INPUT06",
            "section": "ampacity",
            "required": [
                "element_id", "conductor_code", "base_ampacity_a", "norm_id", "ib_a", "in_a",
                "installation_reference", "ampacity_reference", "factors or base_conditions_confirmed",
            ],
            "evidence_expected": "Cálculo/ficha de ampacidad, instalación, demanda Ib y protección In con procedencia.",
        },
        {
            "id": "INPUT07",
            "section": "protection_devices",
            "required": [
                "device id/type/protected_element", "In", "Ue", "breaker Icu or fuse breaking_capacity",
                "standard_reference", "source_reference",
            ],
            "evidence_expected": "Cuadro/ficha del dispositivo. Icu/Ics/Icw no son intercambiables.",
        },
        {
            "id": "INPUT08",
            "section": "tcc",
            "required": [
                "curve_id", "dataset_id", "shape", "time_semantics", "source_type", "source_reference",
                "numeric segments and points",
            ],
            "evidence_expected": "Dataset TCC numérico trazable; clearing requiere TOTAL_CLEARING_TIME dentro de dominio.",
        },
        {
            "id": "INPUT09",
            "section": "fault_bindings",
            "required": [
                "device_id", "fault_bus", "fault_type", "case", "current_quantity=ikss_ka",
                "operating_voltage_kv", "source_reference",
            ],
            "evidence_expected": "Binding P4→P5 explícito por dispositivo; ninguna selección automática.",
        },
        {
            "id": "INPUT10",
            "section": "study_inputs",
            "required": ["requested_scope", "short_circuit_buses", "explicit configurable criteria"],
            "evidence_expected": "Alcance, targets y criterios declarados para la corrida específica.",
        },
    ]


def _criteria() -> list[dict[str, Any]]:
    p7 = p7_completion.evaluar_cierre_p7()
    p8b = real_pilot_intake.obtener_contrato_p8b()
    p8f1 = real_project_dossier_tools.obtener_contrato_p8f1()
    p8f2 = real_project_dossier_tools.obtener_contrato_p8f2()
    p8f3 = real_project_dossier_tools.obtener_contrato_p8f3()
    p8f4 = real_project_dossier_tools.obtener_contrato_p8f4()
    engines = engine_selection.obtener_capacidades_motores()
    iec = (engines.get("studies") or {}).get("iec60909") or {}
    arc = (engines.get("studies") or {}).get("arc_flash_ieee1584") or {}
    first_use_tools = [item.get("tool") for item in p8f4.get("recommended_sequence") or []]

    return [
        _criterion(
            "P8F5-01",
            "engineering_preview_foundation",
            p7.get("engineering_preview_ready") is True
            and p7.get("product_release") == RELEASE
            and p7.get("professional_emission") is False,
            "P7D Engineering Preview 0.9 ready con frontera profesional cerrada.",
            "P7D debe permanecer cerrado antes de habilitar uso real controlado.",
        ),
        _criterion(
            "P8F5-02",
            "real_project_intake_fail_closed",
            p8b.get("electrical_calculation") is False
            and p8b.get("model_mutation") is False
            and p8b.get("automatic_defaults") is False
            and p8b.get("automatic_dispatch") is False
            and p8b.get("crosscheck") is False
            and p8b.get("professional_emission") is False,
            f"{real_pilot_intake.SCHEMA}; admisión sin cálculo, mutación ni defaults automáticos.",
            "P8B debe seguir siendo una admisión read-only y fail-closed.",
        ),
        _criterion(
            "P8F5-03",
            "single_public_real_project_entrypoint",
            p8f1.get("entrypoint") == "generar_dossier_piloto_real"
            and p8f1.get("orchestrator_schema") == real_project_dossier.SCHEMA
            and p8f1.get("success_status") == real_project_dossier.STATUS_READY
            and p8f1.get("integrity_required_before_success") is True
            and p8f1.get("collision_safe_output") is True
            and p8f1.get("automatic_dispatch") is False
            and p8f1.get("automatic_fault_binding") is False
            and p8f1.get("crosscheck") is False
            and p8f1.get("professional_emission") is False,
            "generar_dossier_piloto_real → P8E2; integridad obligatoria; collision-safe; sin auto-dispatch/binding.",
            "La ruta pública real debe seguir delegando en el orquestador probado sin bypass.",
        ),
        _criterion(
            "P8F5-04",
            "dossier_integrity_gate",
            p8f2.get("integrity_schema") == dossier_integrity.SCHEMA
            and p8f2.get("hash_algorithm") == "sha256"
            and p8f2.get("portable_relative_paths") is True
            and p8f2.get("exact_file_set_required") is True
            and p8f2.get("success_status") == dossier_integrity.STATUS_VERIFIED
            and p8f2.get("professional_emission") is False,
            "P8F2 exige conjunto exacto + SHA-256 portable antes de DOSSIER_READY.",
            "El dossier no puede declararse listo sin integridad P8F2 verificable.",
        ),
        _criterion(
            "P8F5-05",
            "repeatability_and_no_silent_overwrite",
            p8f3.get("entrypoint") == "generar_dossier_piloto_real"
            and p8f3.get("output_collision_policy") == "SUFFIX_INCREMENT"
            and p8f3.get("silent_overwrite") is False
            and p8f3.get("blocked_execution_creates_delivery_directory") is False
            and p8f3.get("prior_delivery_mutation_allowed") is False
            and p8f3.get("each_success_requires_independent_integrity_verification") is True
            and p8f3.get("professional_emission") is False,
            "P8F3: SUFFIX_INCREMENT, no overwrite, no entrega en ejecución bloqueada, integridad independiente.",
            "Una corrida nueva no puede alterar silenciosamente una entrega previa.",
        ),
        _criterion(
            "P8F5-06",
            "public_mcp_first_use_contract",
            p8f4.get("transport_smoke") == "MCP_STDIO_SERVER_PY"
            and first_use_tools == [
                "evaluar_admision_piloto_real",
                "generar_dossier_piloto_real",
                "verificar_integridad_dossier_real",
            ]
            and p8f4.get("example_is_project_data") is False
            and p8f4.get("example_requires_replacement_with_project_sources") is True
            and p8f4.get("automatic_repair") is False
            and p8f4.get("automatic_retry") is False
            and p8f4.get("professional_emission") is False,
            "P8F4 define smoke por MCP stdio/server.py y secuencia pública admisión→dossier→integridad.",
            "El primer uso debe seguir probado por protocolo público y sin reparación/retry automático.",
        ),
        _criterion(
            "P8F5-07",
            "deterministic_engine_and_iec60909_boundary",
            engines.get("default_engine") == "opendss"
            and engines.get("automatic_dispatch") is False
            and engines.get("crosscheck") is False
            and iec.get("preferred") == "pandapower"
            and iec.get("implemented") is True
            and iec.get("professional_emission_candidate") is False
            and any("full_conformance_claim=false" in str(item) for item in iec.get("requirements") or []),
            "OpenDSS default; pandapower IEC60909 explícito; full_conformance_claim=false; no cross-check automático.",
            "La política de motores o el límite de conformidad IEC 60909 cambió y requiere nueva revisión.",
        ),
        _criterion(
            "P8F5-08",
            "workspace_v5_and_p8d2_visual_boundary",
            callable(workspace_v5.enhance_file)
            and workspace_p8d2_view.MARKER == "<!-- MCP-P8E1-P8D2-RESULTS-V5 -->"
            and workspace_p8d2_view.EXPECTED_SCHEMA == "MCP_ELECTRICO_P8D2_PROTECTION_RESULTS_V1",
            "Workspace V5 único; vista P8D2 read-only con schema esperado y revisión vigente.",
            "La ruta visual del piloto debe seguir siendo Workspace V5 sin interfaz/cálculo paralelo.",
        ),
        _criterion(
            "P8F5-09",
            "arc_flash_deferred_and_professional_boundary_closed",
            ARC_FLASH_POLICY == "DEFERRED"
            and p7.get("arc_flash_ieee1584") == "DEFERRED"
            and arc.get("implemented") is False
            and arc.get("professional_emission_candidate") is False
            and p8f1.get("professional_emission") is False
            and p8f2.get("professional_emission") is False
            and p8f3.get("professional_emission") is False
            and p8f4.get("professional_emission") is False,
            "P6 IEEE1584=DEFERRED; professional_emission=false en toda la frontera P8.",
            "P8 no puede cerrarse si P6 entra implícitamente o se abre emisión profesional.",
        ),
    ]


def evaluar_cierre_p8() -> dict[str, Any]:
    """Evalúa si puede iniciarse uso controlado con expedientes reales."""
    criteria = _criteria()
    pending = [deepcopy(item) for item in criteria if item["status"] != "DONE"]
    ready = not pending
    return {
        "schema": SCHEMA,
        "phase": "P8",
        "phase_version": "P8-real-pilot-and-hardening",
        "phase_status": PHASE_READY if ready else PHASE_NOT_READY,
        "criteria": deepcopy(criteria),
        "pending_criteria": pending,
        "p8_closed": ready,
        "controlled_real_project_use_ready": ready,
        "engineering_preview_ready": ready,
        "product_release": RELEASE if ready else None,
        "allowed_use": ALLOWED_USE if ready else None,
        "public_entrypoint": "generar_dossier_piloto_real" if ready else None,
        "recommended_preflight": "evaluar_admision_piloto_real" if ready else None,
        "post_delivery_verification": "verificar_integridad_dossier_real" if ready else None,
        "required_project_inputs": required_project_inputs(),
        "example_manifest": "examples/p8_first_use_manifest.json",
        "example_is_project_evidence": False,
        "workspace": "V5",
        "arc_flash_ieee1584": ARC_FLASH_POLICY,
        "iec60909_backend": "pandapower_explicit_experimental",
        "iec60909_full_conformance_claim": False,
        "automatic_defaults": False,
        "automatic_dispatch": False,
        "automatic_fault_binding": False,
        "crosscheck": False,
        "professional_report": False,
        "professional_emission": False,
        "next_activity": "FIRST_CONTROLLED_REAL_PROJECT" if ready else "CLOSE_P8F5_PENDING_CRITERIA",
        "note": (
            "P8 cerrado habilita iniciar expedientes reales bajo Engineering Preview y revisión de ingeniería humana. "
            "No equivale a certificación, conformidad normativa integral, firma profesional ni autorización de emisión."
        ),
    }
