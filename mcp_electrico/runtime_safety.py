"""Guardas de runtime para datos profesionales P2.

Se instalan al registrar las tools MCP. Mantienen dos invariantes que no debe
romper una llamada directa desde la interfaz:

1. crear un circuito nuevo limpia todos los estados auxiliares aunque el nuevo
   circuito reutilice exactamente el mismo nombre;
2. OpenDSS FaultStudy no se ejecuta en un contexto P2 si la representación de
   secuencia cero del escenario/modelo no está lista para OpenDSS.

Los modelos legacy/experimentales sin contexto P2 conservan la herramienta de
FaultStudy existente y su estado UNDER_VALIDATION.
"""

from __future__ import annotations

from functools import wraps
from typing import Any

from opendssdirect import dss

from . import conductor_library, core, professional_data, visual_state, zero_sequence


def _professional_transformers() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for name in dss.Transformers.AllNames():
        item = professional_data.obtener_transformador(str(name))
        if item:
            result.append(item)
    return result


def _three_phase_lines() -> list[str]:
    result: list[str] = []
    for name in dss.Lines.AllNames():
        full = f"Line.{name}"
        try:
            if dss.Circuit.SetActiveElement(full) and int(dss.CktElement.NumPhases()) == 3:
                result.append(full)
        except Exception:
            continue
    return result


def evaluar_faultstudy_opendss() -> dict[str, Any]:
    """Evalúa si FaultStudy puede usar los datos P2 sin defaults/stale Z0."""
    source = professional_data.obtener_red_equivalente()
    transformers = _professional_transformers()
    z0 = zero_sequence.snapshot()
    professional_context = bool(
        source
        or transformers
        or z0.get("source")
        or z0.get("lines")
        or z0.get("transformers")
    )
    if not professional_context:
        return {
            "professional_context": False,
            "ready": True,
            "status": "LEGACY_EXPERIMENTAL",
            "reasons": [],
            "note": "Modelo sin contexto P2; FaultStudy conserva su estado UNDER_VALIDATION.",
        }

    reasons: list[dict[str, str]] = []
    if not source:
        reasons.append({"code": "P2ZFAULT010", "message": "Falta red equivalente P2 positivo-secuencia."})
    else:
        active = str(source.get("active_scenario") or "max")
        z0_source = zero_sequence.obtener_fuente()
        projection = (z0_source or {}).get("active_projection", {})
        if not z0_source:
            reasons.append({"code": "P2ZFAULT011", "message": "Falta R0/X0 explícita de la fuente."})
        elif not projection.get("applied") or str(projection.get("scenario")) != active:
            reasons.append({
                "code": "P2ZFAULT012",
                "message": f"La Z0 aplicada de la fuente no corresponde al escenario activo {active}.",
            })

    for full in _three_phase_lines():
        record = zero_sequence.obtener_linea(full)
        if not record:
            reasons.append({"code": "P2ZFAULT020", "message": f"{full} no tiene R0/X0 explícitos."})
        elif not record.get("projection", {}).get("opendss_ready"):
            reasons.append({"code": "P2ZFAULT021", "message": f"{full} no tiene proyección Z0 OpenDSS lista."})

    for transformer in transformers:
        full = str(transformer.get("id") or f"Transformer.{transformer.get('name')}")
        record = zero_sequence.obtener_transformador(full)
        if not record:
            reasons.append({"code": "P2ZFAULT030", "message": f"{full} no tiene ficha explícita de secuencia cero."})
        elif not record.get("projection", {}).get("opendss_ready"):
            reasons.append({
                "code": "P2ZFAULT031",
                "message": f"{full} tiene ficha Z0, pero su proyección OpenDSS no está validada.",
            })

    return {
        "professional_context": True,
        "ready": not reasons,
        "status": "READY_FOR_OPENDSS_FAULTSTUDY" if not reasons else "BLOCKED_P2",
        "reasons": reasons,
        "note": "La aptitud de datos no cambia la madurez UNDER_VALIDATION de FaultStudy.",
    }


def _reset_auxiliary_state() -> None:
    """Limpia estados ligados al modelo después de crear un Circuit nuevo."""
    visual_state.reset()
    conductor_library.reset()
    professional_data.reset()
    zero_sequence.reset()


def install() -> None:
    """Instala guardas idempotentes sobre las rutas públicas actuales de core."""
    if not getattr(core.crear_circuito, "_mcp_p2_lifecycle_guard", False):
        raw_create = core.crear_circuito

        @wraps(raw_create)
        def guarded_create(*args, **kwargs):
            result = raw_create(*args, **kwargs)
            _reset_auxiliary_state()
            return result

        guarded_create._mcp_p2_lifecycle_guard = True  # type: ignore[attr-defined]
        core.crear_circuito = guarded_create

    if not getattr(core.ejecutar_cortocircuito, "_mcp_p2_fault_guard", False):
        raw_fault = core.ejecutar_cortocircuito

        @wraps(raw_fault)
        def guarded_fault(*args, **kwargs):
            preflight = evaluar_faultstudy_opendss()
            if preflight["professional_context"] and not preflight["ready"]:
                detail = "; ".join(
                    f"{item['code']}: {item['message']}" for item in preflight["reasons"]
                )
                raise ValueError(
                    "P2ZFAULT001: FaultStudy OpenDSS bloqueado para este modelo P2. " + detail
                )
            return raw_fault(*args, **kwargs)

        guarded_fault._mcp_p2_fault_guard = True  # type: ignore[attr-defined]
        core.ejecutar_cortocircuito = guarded_fault
