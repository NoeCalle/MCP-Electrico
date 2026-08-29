"""P8C3B — materializador determinista del manifiesto real admitido por P8B.

Esta capa construye el modelo OpenDSS y las fichas P2/Z0 que ya pueden
representarse sin ejecutar flujo, cortocircuito, ampacidad ni protección.

Reglas:
- P8B debe estar READY antes de cualquier mutación;
- un preflight propio valida requisitos de serialización/materialización;
- frecuencia del sistema es explícita: nunca se usa silenciosamente el default
  de ``core.crear_circuito``;
- el mismo proyecto puede reconstruirse con el mismo nombre sin heredar estado
  P2/Z0/P3/P5/visual del modelo anterior;
- datos fuera del contrato actual no se inventan. Si OpenDSS conserva un valor
  interno por defecto porque el manifiesto no aporta un parámetro opcional, la
  dependencia queda expuesta en ``engine_defaults_retained``;
- no se ejecuta ningún estudio y ``professional_emission`` permanece False.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import re
from typing import Any

from opendssdirect import dss

from . import (
    ampacity,
    conductor_library,
    core,
    professional_data,
    protection_curves,
    protection_data,
    real_pilot_intake,
    visual_state,
    workspace_state,
    zero_sequence,
)

SCHEMA = "MCP_ELECTRICO_P8C3_REAL_MODEL_MATERIALIZER_V1"
STATUS_BLOCKED_INTAKE = "BLOCKED_BY_P8B_INTAKE"
STATUS_BLOCKED_PREFLIGHT = "BLOCKED_BY_MATERIALIZER_PREFLIGHT"
STATUS_BUILT = "MODEL_BUILT_NOT_EXECUTED"
STATUS_FAILED = "BUILD_FAILED_PARTIAL_MODEL"
GROUND_SCOPE = "IEC60909_1PH_GROUND_MAX_MIN"

_SAFE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
_ALLOWED_VECTOR_GROUPS = {
    "dd0",
    "yy0",
    "yyn0",
    "dyn1",
    "dyn11",
    "yd1",
    "yd11",
}


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _number(value: Any) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _issue(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}


def _manifest_hash(manifest: dict[str, Any]) -> str:
    payload = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(payload.encode("utf-8")).hexdigest()


def _circuit_name(project_id: str) -> str:
    raw = str(project_id).strip()
    safe = re.sub(r"[^A-Za-z0-9_]+", "_", raw).strip("_") or "project"
    if safe[0].isdigit():
        safe = f"p_{safe}"
    digest = sha256(raw.encode("utf-8")).hexdigest()[:8]
    return f"p8_{safe[:40]}_{digest}"


def _element_name(identifier: Any, expected_class: str) -> str:
    raw = str(identifier or "").strip()
    if "." in raw:
        kind, name = raw.split(".", 1)
        if kind.lower() != expected_class.lower():
            raise ValueError(f"ID {raw!r} debe pertenecer a {expected_class}.*")
    else:
        name = raw
    if not name or not _SAFE_NAME.fullmatch(name):
        raise ValueError(
            f"nombre OpenDSS no soportado por P8C3B: {raw!r}; use letras, números, '_' o '-' sin espacios"
        )
    return name


def _source_bus() -> str:
    try:
        dss("? Vsource.source.bus1")
        return str(dss.Text.Result() or "").split(".")[0].strip()
    except Exception:
        return ""


def _reference(item: dict[str, Any], project_reference: str) -> tuple[str, str | None]:
    ref = str(item.get("source_reference") or project_reference).strip()
    url = str(item.get("source_url") or "").strip() or None
    return ref, url


def _preflight(manifest: dict[str, Any]) -> list[dict[str, str]]:
    """Valida serialización/materialización sin tocar OpenDSS."""
    issues: list[dict[str, str]] = []
    source = manifest.get("source") or {}
    topology = manifest.get("topology") or {}

    frequency = source.get("frequency_hz")
    if not _present(frequency):
        issues.append(_issue(
            "P8C3B001",
            "source.frequency_hz",
            "La frecuencia debe declararse explícitamente; P8C3B no usa el default 60 Hz del motor.",
        ))
    elif not _number(frequency) or float(frequency) <= 0:
        issues.append(_issue("P8C3B002", "source.frequency_hz", "frequency_hz debe ser numérica y mayor que cero."))

    for path, raw in [("source.bus", source.get("bus"))] + [
        (f"topology.buses[{i}]", bus) for i, bus in enumerate(topology.get("buses") or [])
    ]:
        text = str(raw or "").strip()
        if text and not _SAFE_NAME.fullmatch(text):
            issues.append(_issue(
                "P8C3B003",
                path,
                "P8C3B v1 requiere nombres de barra sin espacios ni nodos embebidos; use letras, números, '_' o '-'.",
            ))

    for collection, expected in (("transformers", "Transformer"), ("lines", "Line"), ("loads", "Load")):
        for i, item in enumerate(topology.get(collection) or []):
            if not isinstance(item, dict):
                continue
            try:
                _element_name(item.get("id"), expected)
            except ValueError as exc:
                issues.append(_issue("P8C3B004", f"topology.{collection}[{i}].id", str(exc)))

    for i, item in enumerate(topology.get("lines") or []):
        if not isinstance(item, dict):
            continue
        phases = item.get("phases")
        if _number(phases) and (float(phases) not in {1.0, 2.0, 3.0}):
            issues.append(_issue("P8C3B005", f"topology.lines[{i}].phases", "fases debe ser exactamente 1, 2 o 3."))

    for i, item in enumerate(topology.get("loads") or []):
        if not isinstance(item, dict):
            continue
        phases = item.get("phases")
        if _number(phases) and (float(phases) not in {1.0, 2.0, 3.0}):
            issues.append(_issue("P8C3B006", f"topology.loads[{i}].phases", "fases debe ser exactamente 1, 2 o 3."))
        connection = item.get("connection")
        if _present(connection) and str(connection).strip().lower() not in {"wye", "delta"}:
            issues.append(_issue("P8C3B007", f"topology.loads[{i}].connection", "connection debe ser wye o delta cuando se declara."))
        model = item.get("model")
        if _present(model) and (not _number(model) or int(float(model)) != float(model) or int(float(model)) not in range(1, 9)):
            issues.append(_issue("P8C3B008", f"topology.loads[{i}].model", "OpenDSS Load.Model debe ser un entero entre 1 y 8."))

    for i, item in enumerate(topology.get("transformers") or []):
        if not isinstance(item, dict):
            continue
        group = str(item.get("vector_group") or "").strip().lower()
        if group and group not in _ALLOWED_VECTOR_GROUPS:
            issues.append(_issue(
                "P8C3B009",
                f"topology.transformers[{i}].vector_group",
                "P8C3B v1 admite Dd0, Yy0/Yyn0, Dyn1, Dyn11, Yd1 o Yd11; no se aproxima otro grupo.",
            ))

        tap_fields = ("tap_side", "tap_neutral", "tap_min", "tap_max", "tap_step_percent", "tap_pos")
        declared_tap = [key for key in tap_fields if _present(item.get(key))]
        if declared_tap and len(declared_tap) != len(tap_fields):
            issues.append(_issue(
                "P8C3B010",
                f"topology.transformers[{i}]",
                "Si se declara regulación de tap, P8C3B exige tap_side, neutral, min, max, step y posición completos.",
            ))

    max_pair = (_present(source.get("scc_max_mva")), _present(source.get("x_r_max")))
    min_pair = (_present(source.get("scc_min_mva")), _present(source.get("x_r_min")))
    if any(max_pair) and not all(max_pair):
        issues.append(_issue("P8C3B011", "source", "scc_max_mva y x_r_max deben declararse juntos."))
    if any(min_pair) and not all(min_pair):
        issues.append(_issue("P8C3B012", "source", "scc_min_mva y x_r_min deben declararse juntos."))
    if all(min_pair) and not all(max_pair):
        issues.append(_issue("P8C3B013", "source", "No se materializa escenario MIN sin equivalente MAX P2."))

    return issues


def _reset_runtime_state() -> list[str]:
    """Limpia stores que podrían sobrevivir si se recrea el mismo nombre de circuito."""
    professional_data.reset()
    zero_sequence.reset()
    conductor_library.reset()
    ampacity.reset()
    protection_data.reset()
    protection_curves.reset()
    visual_state.reset()
    workspace_state.reset_for_circuit("p8c3b_materializer_start")
    return [
        "professional_data",
        "zero_sequence",
        "conductor_library",
        "ampacity",
        "protection_data",
        "protection_curves",
        "visual_state",
        "workspace_state",
    ]


def _engine_default_dependencies(manifest: dict[str, Any], p2: dict[str, Any]) -> list[dict[str, str]]:
    """Hace visibles valores que el MCP no inventó pero que el motor puede retener."""
    dependencies: list[dict[str, str]] = []
    source = manifest.get("source") or {}
    if not _present(source.get("pu")):
        dependencies.append({"path": "source.pu", "note": "Vsource conserva el pu interno de OpenDSS; no se presenta como dato profesional."})
    if not _present(source.get("angle_deg")):
        dependencies.append({"path": "source.angle_deg", "note": "Vsource conserva el ángulo interno de OpenDSS; no se presenta como dato profesional."})

    for i, line in enumerate((manifest.get("topology") or {}).get("lines") or []):
        if isinstance(line, dict) and not _present(line.get("c1_nf_km")):
            dependencies.append({
                "path": f"topology.lines[{i}].c1_nf_km",
                "note": "C1 no fue suministrada; OpenDSS conserva su valor interno. P8C3B no la inventa.",
            })

    for i, load in enumerate((manifest.get("topology") or {}).get("loads") or []):
        if not isinstance(load, dict):
            continue
        if not _present(load.get("connection")):
            dependencies.append({"path": f"topology.loads[{i}].connection", "note": "Conexión de carga no declarada; se conserva el valor interno OpenDSS."})
        if not _present(load.get("model")):
            dependencies.append({"path": f"topology.loads[{i}].model", "note": "Modelo de carga no declarado; se conserva el valor interno OpenDSS."})

    for item in p2.get("transformers", []):
        for note in (item.get("projection", {}).get("opendss", {}).get("assumptions") or []):
            dependencies.append({"path": str(item.get("id") or "Transformer"), "note": str(note)})
        if not item.get("tap", {}).get("enabled"):
            dependencies.append({
                "path": f"{item.get('id')}.tap",
                "note": "No se declaró regulación completa; P2 conserva tap nominal 1.0 y no afirma un tap de proyecto.",
            })
    return dependencies


def _evidence() -> dict[str, Any]:
    return {
        "circuit": str(dss.Circuit.Name() or ""),
        "source_bus": _source_bus(),
        "buses": sorted(str(x) for x in dss.Circuit.AllBusNames()),
        "transformers": sorted(f"Transformer.{x}" for x in dss.Transformers.AllNames()),
        "lines": sorted(f"Line.{x}" for x in dss.Lines.AllNames()),
        "loads": sorted(f"Load.{x}" for x in dss.Loads.AllNames()),
    }


def materializar_modelo(manifest: dict[str, Any]) -> dict[str, Any]:
    """Construye OpenDSS/P2/Z0 a partir de un manifiesto admitido, sin Solve."""
    if not isinstance(manifest, dict):
        raise TypeError("manifest debe ser dict.")

    manifest_copy = deepcopy(manifest)
    admission = real_pilot_intake.evaluar_admision(manifest_copy)
    base = {
        "schema": SCHEMA,
        "manifest_sha256": _manifest_hash(manifest_copy),
        "p8b_intake_status": admission["intake_status"],
        "requested_scope": deepcopy(admission.get("requested_scope") or []),
        "electrical_calculation_performed": False,
        "studies_executed": [],
        "automatic_defaults": False,
        "automatic_dispatch": False,
        "crosscheck": False,
        "professional_emission": False,
    }
    if not admission.get("ready_to_build_model"):
        return {
            **base,
            "materializer_status": STATUS_BLOCKED_INTAKE,
            "model_mutation_performed": False,
            "ready_for_engine_preflight": False,
            "issues": deepcopy(admission.get("issues") or []),
            "p8b": admission,
        }

    preflight = _preflight(manifest_copy)
    if preflight:
        return {
            **base,
            "materializer_status": STATUS_BLOCKED_PREFLIGHT,
            "model_mutation_performed": False,
            "ready_for_engine_preflight": False,
            "issues": preflight,
            "p8b": admission,
        }

    project = manifest_copy["project"]
    source = manifest_copy["source"]
    topology = manifest_copy["topology"]
    project_reference = str(project["source_reference"]).strip()
    circuit_name = _circuit_name(str(project["id"]))
    mutated = False
    reset_modules: list[str] = []

    try:
        core.crear_circuito(
            circuit_name,
            float(source["kv_ll"]),
            frecuencia=float(source["frequency_hz"]),
            bus_fuente=str(source["bus"]),
        )
        mutated = True
        reset_modules = _reset_runtime_state()

        source_ref, source_url = _reference(source, project_reference)
        if _present(source.get("pu")):
            dss(f"Edit Vsource.source pu={float(source['pu'])}")
        if _present(source.get("angle_deg")):
            dss(f"Edit Vsource.source angle={float(source['angle_deg'])}")

        source_p2 = None
        if _present(source.get("scc_max_mva")) and _present(source.get("x_r_max")):
            source_p2 = professional_data.definir_red_equivalente(
                kv_ll=float(source["kv_ll"]),
                scc_max_mva=float(source["scc_max_mva"]),
                x_r_max=float(source["x_r_max"]),
                scc_min_mva=float(source["scc_min_mva"]) if _present(source.get("scc_min_mva")) else None,
                x_r_min=float(source["x_r_min"]) if _present(source.get("x_r_min")) else None,
                escenario_activo="max",
                fuente_referencia=source_ref,
                fuente_url=source_url,
                bus_fuente=str(source["bus"]),
            )

        created_transformers: list[dict[str, Any]] = []
        for item in topology.get("transformers") or []:
            name = _element_name(item["id"], "Transformer")
            ref, url = _reference(item, project_reference)
            tap_declared = all(_present(item.get(key)) for key in (
                "tap_side", "tap_neutral", "tap_min", "tap_max", "tap_step_percent", "tap_pos"
            ))
            created_transformers.append(professional_data.agregar_transformador_profesional(
                nombre=name,
                bus_hv=str(item["bus_hv"]),
                bus_lv=str(item["bus_lv"]),
                kva=float(item["kva"]),
                kv_hv=float(item["kv_hv"]),
                kv_lv=float(item["kv_lv"]),
                uk_percent=float(item["uk_percent"]),
                grupo_vectorial=str(item["vector_group"]),
                x_r=float(item["x_r"]) if _present(item.get("x_r")) else None,
                load_loss_kw=float(item["load_loss_kw"]) if _present(item.get("load_loss_kw")) else None,
                no_load_loss_kw=float(item["no_load_loss_kw"]) if _present(item.get("no_load_loss_kw")) else None,
                i0_percent=float(item["i0_percent"]) if _present(item.get("i0_percent")) else None,
                tap_side=str(item["tap_side"]) if tap_declared else None,
                tap_neutral=int(item["tap_neutral"]) if tap_declared else 0,
                tap_min=int(item["tap_min"]) if tap_declared else 0,
                tap_max=int(item["tap_max"]) if tap_declared else 0,
                tap_step_percent=float(item["tap_step_percent"]) if tap_declared else None,
                tap_pos=int(item["tap_pos"]) if tap_declared else 0,
                fabricante=str(item.get("manufacturer") or "").strip() or None,
                modelo=str(item.get("model") or "").strip() or None,
                fuente_referencia=ref,
                fuente_url=url,
            ))

        for item in topology.get("lines") or []:
            name = _element_name(item["id"], "Line")
            core.agregar_linea(
                name,
                str(item["bus1"]),
                str(item["bus2"]),
                float(item["length_km"]),
                fases=int(float(item["phases"])),
                r1_ohm_km=float(item["r1_ohm_km"]),
                x1_ohm_km=float(item["x1_ohm_km"]),
            )
            if _present(item.get("c1_nf_km")):
                dss(f"Edit Line.{name} C1={float(item['c1_nf_km'])}")

        for item in topology.get("loads") or []:
            name = _element_name(item["id"], "Load")
            core.agregar_carga(
                name,
                str(item["bus"]),
                float(item["kw"]),
                float(item["kvar"]),
                fases=int(float(item["phases"])),
                kv=float(item["kv"]),
                critica=bool(item.get("critical", False)),
            )
            edits: list[str] = []
            if _present(item.get("connection")):
                edits.append(f"Conn={str(item['connection']).lower()}")
            if _present(item.get("model")):
                edits.append(f"Model={int(float(item['model']))}")
            if edits:
                dss(f"Edit Load.{name} {' '.join(edits)}")

        if GROUND_SCOPE in set(base["requested_scope"]):
            z0 = manifest_copy["zero_sequence"]
            z0_source = z0["source"]
            ref, url = _reference(z0_source, project_reference)
            zero_sequence.definir_fuente(
                r0_max_ohm=float(z0_source["r0_max_ohm"]),
                x0_max_ohm=float(z0_source["x0_max_ohm"]),
                r0_min_ohm=float(z0_source["r0_min_ohm"]),
                x0_min_ohm=float(z0_source["x0_min_ohm"]),
                fuente_referencia=ref,
                fuente_url=url,
            )

            for item in z0.get("lines") or []:
                name = _element_name(item["id"], "Line")
                ref, url = _reference(item, project_reference)
                zero_sequence.definir_linea(
                    f"Line.{name}",
                    r0_ohm_km=float(item["r0_ohm_km"]),
                    x0_ohm_km=float(item["x0_ohm_km"]),
                    c0_nf_km=float(item["c0_nf_km"]),
                    fuente_referencia=ref,
                    fuente_url=url,
                )

            for item in z0.get("transformers") or []:
                name = _element_name(item["id"], "Transformer")
                ref, url = _reference(item, project_reference)
                zero_sequence.definir_transformador(
                    f"Transformer.{name}",
                    uk0_percent=float(item["uk0_percent"]),
                    ur0_percent=float(item["ur0_percent"]),
                    magnetizing_z0_ratio_percent=float(item["magnetizing_z0_ratio_percent"]),
                    magnetizing_r_over_x=float(item["magnetizing_r_over_x"]),
                    leakage_share_hv=float(item["leakage_share_hv"]),
                    neutral_side=str(item["neutral_side"]),
                    neutral_mode=str(item["neutral_mode"]),
                    rn_ohm=float(item["rn_ohm"]) if _present(item.get("rn_ohm")) else None,
                    xn_ohm=float(item["xn_ohm"]) if _present(item.get("xn_ohm")) else None,
                    fuente_referencia=ref,
                    fuente_url=url,
                )

        workspace_state.reset_for_circuit("p8c3b_model_materialized")
        p2_snapshot = professional_data.snapshot()
        z0_snapshot = zero_sequence.snapshot()
        evidence = _evidence()
        dependencies = _engine_default_dependencies(manifest_copy, p2_snapshot)
        materialized_payload = {
            "manifest_sha256": base["manifest_sha256"],
            "evidence": evidence,
            "p2": p2_snapshot,
            "z0": z0_snapshot,
        }
        fingerprint = sha256(
            json.dumps(materialized_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        ).hexdigest()
        return {
            **base,
            "materializer_status": STATUS_BUILT,
            "model_mutation_performed": True,
            "ready_for_engine_preflight": True,
            "issues": [],
            "circuit_name": circuit_name,
            "runtime_resets": reset_modules,
            "source_p2_materialized": source_p2 is not None,
            "materialized_fingerprint_sha256": fingerprint,
            "evidence": evidence,
            "p2": p2_snapshot,
            "zero_sequence": z0_snapshot,
            "engine_defaults_retained": dependencies,
            "engine_defaults_retained_count": len(dependencies),
            "workspace": workspace_state.status(),
            "note": (
                "Modelo construido y no resuelto. engine_defaults_retained identifica parámetros opcionales "
                "que el MCP no inventó y que deben cerrarse antes del gate de ejecución que los requiera."
            ),
        }
    except Exception as exc:
        return {
            **base,
            "materializer_status": STATUS_FAILED,
            "model_mutation_performed": mutated,
            "ready_for_engine_preflight": False,
            "issues": [{
                "code": "P8C3B900",
                "path": "materialization",
                "message": f"{type(exc).__name__}: {exc}",
            }],
            "circuit_name": str(dss.Circuit.Name() or ""),
            "runtime_resets": reset_modules,
            "evidence": _evidence() if mutated else None,
        }
