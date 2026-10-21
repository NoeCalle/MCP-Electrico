"""Selección determinista de backend por tipo de estudio.

Esta capa no ejecuta estudios. Decide qué backend corresponde, qué
alternativas existen, qué requisitos deben cumplirse y si el estudio está
habilitado en la madurez/modelo actuales.

No ejecuta ni compara motores. La entrada explícita ejecutar_estudio conecta
las rutas admitidas con sus ejecutores públicos y sus gates independientes.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any
import unicodedata

from opendssdirect import dss

from . import model_qa, pandapower_engine, study_readiness, validation_status, module_qualification
from .external_engine_catalogue import EXTERNAL_ENGINES, PLANNED_STUDI…11082 tokens truncated…"], snapshot)

        report = project_report.construir_reporte(snapshot)
        if not report.get("ok"):
            raise RuntimeError(f"P8E2R001: P7C bloqueado: {report}")
        paths["report"].write_text(str(report["html"]), encoding="utf-8")

        reconstruction = _p7b_isolated(
            paths["snapshot"],
            paths["reconstructed"],
            paths["reconstruction"],
        )
        if reconstruction.get("status") != P7B_OK:
            raise RuntimeError(f"P8E2B001: P7B aislado no verificó round-trip: {reconstruction}")
        if reconstruction.get("isolation_mode") != P7B_ISOLATION_MODE:
            raise RuntimeError(f"P8E2ISO002: P7B no usó el contexto DSS aislado esperado: {reconstruction}")
        if reconstruction.get("parent_dss_context_mutated") is not False:
            raise RuntimeError(f"P8E2ISO003: P7B no confirmó preservación del contexto DSS padre: {reconstruction}")

        circuit_after = _active_circuit()
        revision_after = workspace_state.status().get("model_revision")
        if circuit_after != circuit_before or revision_after != revision_before:
            raise RuntimeError(
                "P8E2ISO001: la verificación P7B aislada alteró el circuito/revisión del proceso principal."
            )

        integrity_context = {
            "manifest_sha256": manifest_sha,
            "model_revision": revision_after,
            "p8d2_schema": execution.get("schema"),
            "p8d2_execution_status": execution.get("execution_status"),
            "declared_design_check_status": assessment["status"],
            "p7a_payload_sha256": (snapshot.get("hash") or {}).get("value"),
            "p7c_report_sha256": (report.get("report_hash") or {}).get("value"),
            "p7c_source_snapshot_sha256": (report.get("data") or {}).get("source_snapshot", {}).get("sha256"),
            "workspace_version": 5,
            "p7b_isolation_mode": P7B_ISOLATION_MODE,
            "professional_emission": False,
        }
        integrity = dossier_integrity.construir_indice(target, context=integrity_context)
        integrity_verification = integrity.get("verification") or {}
        if integrity_verification.get("status") != dossier_integrity.STATUS_VERIFIED:
            raise RuntimeError(
                f"P8F2I001: índice de integridad del dossier no verificó: {integrity_verification}"
            )

        return {
            "schema": SCHEMA,
            "status": STATUS_READY,
            "manifest_sha256": manifest_sha,
            "requested_output_directory": str(requested_output),
            "output_directory": str(target),
            "output_directory_collision_avoided": collision_avoided,
            "model_revision": revision_after,
            "active_circuit_preserved": True,
            "p8d2_execution_status": execution.get("execution_status"),
            "design_assessment": assessment,
            "design_checks_path": str(paths["assessment"]),
            "workspace": {
                "status": "WORKSPACE_V5_READY",
                "path": str(paths["workspace"]),
                "p8d2_integrated_view": True,
                "browser_engineering_calculation": False,
            },
            "p7a": {
                "status": verification.get("status"),
                "snapshot_path": str(paths["snapshot"]),
                "sha256": (snapshot.get("hash") or {}).get("value"),
            },
            "p7b": {
                "status": reconstruction.get("status"),
                "result_path": str(paths["reconstruction"]),
                "isolated_process": False,
                "isolated_context": True,
                "isolation_mode": P7B_ISOLATION_MODE,
                "parent_dss_context_mutated": False,
                "parent_structured_state_mutated": False,
                "stored_results_promoted_to_current": False,
            },
            "p7c": {
                "status": report.get("status"),
                "report_path": str(paths["report"]),
                "report_sha256": (report.get("report_hash") or {}).get("value"),
                "source_snapshot_sha256": (report.get("data") or {}).get("source_snapshot", {}).get("sha256"),
                "browser_engineering_calculation": False,
            },
            "integrity": {
                "status": integrity_verification.get("status"),
                "ok": integrity_verification.get("ok"),
                "index_path": str(paths["integrity"]),
                "payload_sha256": integrity_verification.get("payload_sha256"),
                "index_file_sha256": integrity.get("index_file_sha256"),
                "verified_file_count": integrity_verification.get("verified_file_count"),
                "portable_relative_paths": True,
                "self_hash_included": False,
            },
            "trace_files": {
                "manifest": str(paths["manifest"]),
                "execution_p8d2": str(paths["execution"]),
                "integrity_index": str(paths["integrity"]),
            },
            "automatic_dispatch": False,
            "automatic_fault_binding": False,
            "p4_recalculation_inside_p5": False,
            "crosscheck": False,
            "professional_report": False,
            "professional_emission": False,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": STATUS_FAILED_ARTIFACT,
            "manifest_sha256": manifest_sha,
            "requested_output_directory": str(requested_output),
            "output_directory": str(target),
            "output_directory_collision_avoided": collision_avoided,
            "error": str(exc),
            "active_circuit_preserved": _active_circuit() == circuit_before,
            "model_revision_preserved": workspace_state.status().get("model_revision") == revision_before,
            "integrity_index_generated": paths["integrity"].is_file(),
            "p7b_isolated": True,
            "p7b_isolation_mode": P7B_ISOLATION_MODE,
            "automatic_dispatch": False,
            "crosscheck": False,
            "professional_emission": False,
        }
