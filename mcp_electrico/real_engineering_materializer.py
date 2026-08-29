"""P8C4A — materialización de datos de ingeniería P3 sobre el modelo real.

P8C3B reconstruye OpenDSS/P2/Z0. P8C4A conserva ese builder eléctrico puro y
agrega, en una capa posterior, el binding real de conductor + Ib/In/Iz base para
P3. No ejecuta flujo, ampacidad ni protección.

Principios:
- el modelo base debe alcanzar MODEL_BUILT_NOT_EXECUTED;
- todos los registros P3 se validan antes de crear una sola asignación P3;
- un conductor de proyecto no se disfraza como producto del catálogo interno;
- R1/X1 del expediente no se sustituyen durante el binding P3;
- Iz_base, Ib, In, norma y condiciones/factores conservan referencias separadas;
- P5 permanece explícitamente pendiente para P8C4B;
- automatic_defaults/dispatch/crosscheck/professional_emission permanecen False.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from math import isfinite
from typing import Any

from opendssdirect import dss

from . import (
    ampacity,
    ampacity_norms,
    conductor_library,
    real_model_materializer,
    workspace_state,
)

SCHEMA = "MCP_ELECTRICO_P8C4A_REAL_ENGINEERING_MATERIALIZER_V1"
STATUS_BLOCKED_BUILD = "BLOCKED_BY_MODEL_BUILD"
STATUS_BLOCKED_P3 = "BLOCKED_BY_P3_PREFLIGHT"
STATUS_P3_MATERIALIZED = "P3_MATERIALIZED_P5_PENDING"
STATUS_NOT_REQUESTED = "P3_NOT_REQUESTED"
AMPACITY_SCOPE = "AMPACITY"
PROTECTION_SCOPE = "PROTECTION_TCC"


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _positive(value: Any) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return isfinite(number) and number > 0


def _issue(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}


def _line_exists(identifier: str) -> bool:
    return bool(identifier) and identifier.lower().startswith("line.") and bool(dss.Circuit.SetActiveElement(identifier))


def _p3_preflight(manifest: dict[str, Any]) -> list[dict[str, str]]:
    records = manifest.get("ampacity") or []
    issues: list[dict[str, str]] = []
    seen: set[str] = set()

    if not isinstance(records, list) or not records:
        return [_issue("P8C4A001", "ampacity", "AMPACITY requiere al menos una ficha P3 materializable.")]

    for i, item in enumerate(records):
        path = f"ampacity[{i}]"
        if not isinstance(item, dict):
            issues.append(_issue("P8C4A002", path, "La ficha P3 debe ser un objeto estructurado."))
            continue

        required = (
            "element_id",
            "conductor_code",
            "base_ampacity_a",
            "norm_id",
            "ib_a",
            "ib_reference",
            "in_a",
            "in_reference",
            "installation_reference",
            "ampacity_reference",
        )
        for key in required:
            if not _present(item.get(key)):
                issues.append(_issue("P8C4A003", f"{path}.{key}", f"Entrada P3 materializable requerida: {key}."))

        element = str(item.get("element_id") or "").strip()
        if element:
            key = element.lower()
            if key in seen:
                issues.append(_issue("P8C4A004", f"{path}.element_id", "No se permiten dos fichas P3 para el mismo elemento."))
            seen.add(key)
            if not element.lower().startswith("line."):
                issues.append(_issue("P8C4A005", f"{path}.element_id", "P3 v1 solo materializa ampacidad sobre Line.*."))
            elif not _line_exists(element):
                issues.append(_issue("P8C4A006", f"{path}.element_id", "La línea P3 no existe en el modelo P8C3B activo."))

        for key in ("base_ampacity_a", "ib_a", "in_a"):
            if _present(item.get(key)) and not _positive(item.get(key)):
                issues.append(_issue("P8C4A007", f"{path}.{key}", f"{key} debe ser finito y mayor que cero."))

        norm_id = str(item.get("norm_id") or "").strip()
        if norm_id:
            try:
                ampacity_norms.obtener_referencia(norm_id)
            except KeyError as exc:
                issues.append(_issue("P8C4A008", f"{path}.norm_id", str(exc)))

        factors = item.get("factors") or []
        confirmed = item.get("base_conditions_confirmed") is True
        if factors and confirmed:
            issues.append(_issue(
                "P8C4A009",
                path,
                "Use factors explícitos o base_conditions_confirmed=true, no ambos.",
            ))
        if not factors and not confirmed:
            issues.append(_issue(
                "P8C4A010",
                path,
                "P3 no asume factor total 1.0: declare factors o base_conditions_confirmed=true.",
            ))
        if factors and not isinstance(factors, list):
            issues.append(_issue("P8C4A011", f"{path}.factors", "factors debe ser una lista."))
        elif isinstance(factors, list):
            for j, factor in enumerate(factors):
                fpath = f"{path}.factors[{j}]"
                if not isinstance(factor, dict):
                    issues.append(_issue("P8C4A012", fpath, "Cada factor P3 debe ser un objeto."))
                    continue
                for key in ("id", "value", "reference"):
                    if not _present(factor.get(key)):
                        issues.append(_issue("P8C4A013", f"{fpath}.{key}", f"Factor P3 requiere {key}."))
                if _present(factor.get("value")):
                    try:
                        value = float(factor["value"])
                    except (TypeError, ValueError):
                        value = float("nan")
                    if not isfinite(value) or value <= 0 or value > 2.0:
                        issues.append(_issue("P8C4A014", f"{fpath}.value", "Factor P3 debe ser >0 y <=2.0."))

    return issues


def _fingerprint(model_fingerprint: str | None, assignments: dict[str, Any], profiles: list[dict[str, Any]]) -> str:
    payload = {
        "model_fingerprint": model_fingerprint,
        "assignments": assignments,
        "profiles": profiles,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(raw.encode("utf-8")).hexdigest()


def materializar_datos_ingenieria(manifest: dict[str, Any]) -> dict[str, Any]:
    """Reconstruye P8C3B y materializa P3 sin ejecutar evaluaciones."""
    if not isinstance(manifest, dict):
        raise TypeError("manifest debe ser dict.")

    manifest_copy = deepcopy(manifest)
    model = real_model_materializer.materializar_modelo(manifest_copy)
    requested = [str(x).strip().upper() for x in manifest_copy.get("requested_scope") or [] if str(x).strip()]
    base = {
        "schema": SCHEMA,
        "requested_scope": requested,
        "model_materialization_status": model.get("materializer_status"),
        "model_fingerprint_sha256": model.get("materialized_fingerprint_sha256"),
        "electrical_calculation_performed": False,
        "ampacity_calculation_performed": False,
        "protection_calculation_performed": False,
        "studies_executed": [],
        "automatic_defaults": False,
        "automatic_dispatch": False,
        "crosscheck": False,
        "professional_emission": False,
    }

    if model.get("materializer_status") != real_model_materializer.STATUS_BUILT:
        return {
            **base,
            "engineering_materializer_status": STATUS_BLOCKED_BUILD,
            "p3_materialized": False,
            "p5_materialized": False,
            "issues": deepcopy(model.get("issues") or []),
            "model": model,
        }

    if AMPACITY_SCOPE not in set(requested):
        return {
            **base,
            "engineering_materializer_status": STATUS_NOT_REQUESTED,
            "p3_materialized": False,
            "p5_materialized": False,
            "issues": [],
            "model": model,
            "workspace": workspace_state.status(),
        }

    preflight = _p3_preflight(manifest_copy)
    if preflight:
        return {
            **base,
            "engineering_materializer_status": STATUS_BLOCKED_P3,
            "p3_materialized": False,
            "p5_materialized": False,
            "issues": preflight,
            "model": model,
            "conductor_assignments": conductor_library.snapshot_asignaciones(),
            "workspace": workspace_state.status(),
        }

    profiles: list[dict[str, Any]] = []
    assignments: list[dict[str, Any]] = []
    try:
        for item in manifest_copy.get("ampacity") or []:
            element = str(item["element_id"]).strip()
            assignment = conductor_library.registrar_asignacion_proyecto(
                nombre_elemento=element,
                codigo=str(item["conductor_code"]),
                ampacidad_base_a=float(item["base_ampacity_a"]),
                referencia_ampacidad=str(item["ampacity_reference"]),
                referencia_instalacion=str(item["installation_reference"]),
                descripcion=str(item.get("conductor_description") or "").strip() or None,
                fuente_url=str(item.get("source_url") or "").strip() or None,
            )
            assignments.append(assignment)

            factors = deepcopy(item.get("factors") or [])
            profile = ampacity.definir_condiciones(
                nombre_elemento=element,
                norma_id=str(item["norm_id"]),
                in_proteccion_a=float(item["in_a"]),
                factores=factors,
                confirmar_condiciones_base=item.get("base_conditions_confirmed") is True,
                ib_diseno_a=float(item["ib_a"]),
                usar_corriente_flujo_como_ib=False,
                referencia_in=str(item["in_reference"]),
                referencia_ib=str(item["ib_reference"]),
                referencia_condiciones_instalacion=str(item["installation_reference"]),
            )
            profiles.append(profile)

        assignment_snapshot = conductor_library.snapshot_asignaciones()
        fingerprint = _fingerprint(
            model.get("materialized_fingerprint_sha256"),
            assignment_snapshot,
            profiles,
        )
        return {
            **base,
            "engineering_materializer_status": STATUS_P3_MATERIALIZED,
            "p3_materialized": True,
            "p5_materialized": False,
            "issues": [],
            "p3": {
                "profiles": profiles,
                "assignments": assignments,
                "assignment_snapshot": assignment_snapshot,
                "engineering_fingerprint_sha256": fingerprint,
            },
            "p5": {
                "status": "PENDING_P8C4B",
                "devices_materialized": 0,
                "tcc_datasets_materialized": 0,
            },
            "model": model,
            "workspace": workspace_state.status(),
            "note": (
                "P3 fue materializado como datos de ingeniería y no evaluado. P5/TCC permanece pendiente; "
                "ningún estudio ni criterio de cumplimiento fue ejecutado."
            ),
        }
    except Exception as exc:
        # P8C4A valida todo antes de empezar, pero cualquier diferencia interna
        # se expone sin convertir una materialización parcial en READY.
        return {
            **base,
            "engineering_materializer_status": "P3_MATERIALIZATION_FAILED",
            "p3_materialized": False,
            "p5_materialized": False,
            "issues": [{
                "code": "P8C4A900",
                "path": "ampacity",
                "message": f"{type(exc).__name__}: {exc}",
            }],
            "model": model,
            "conductor_assignments": conductor_library.snapshot_asignaciones(),
            "workspace": workspace_state.status(),
        }
