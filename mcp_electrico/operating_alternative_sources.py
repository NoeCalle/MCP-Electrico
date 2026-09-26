"""P12E — fuentes alternativas Thevenin y transferencia explícita.

Esta capa es deliberadamente multiindustria. Representa una fuente alternativa
mediante un Vsource de OpenDSS con equivalente positivo-secuencia explícito.
No modela gobernador, AVR, dinámica de máquina, inversor ni sincronización.

La fuente se crea deshabilitada. Solo una acción explícita ENABLE_ALT_SOURCE
puede energizarla, y el contrato exige aislamiento break-before-make mediante
OPEN_ELEMENT previos en el mismo escenario.
"""

from __future__ import annotations

from math import isfinite, sqrt
from typing import Any

from opendssdirect import dss

SOURCE_TYPE = "THEVENIN_VSOURCE_EQUIVALENT"
ALLOWED_SOURCE_ACTIONS = {"ENABLE_ALT_SOURCE", "DISABLE_ALT_SOURCE"}


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _positive(value: Any) -> bool:
    number = _number(value)
    return number is not None and number > 0


def _issue(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}


def normalize_source_id(raw: Any) -> str:
    text = str(raw or "").strip()
    if text and "." not in text:
        text = f"Vsource.{text}"
    return text


def source_map(package: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in package.get("alternative_sources") or []:
        if not isinstance(item, dict):
            continue
        identifier = normalize_source_id(item.get("id"))
        if identifier:
            result[identifier.lower()] = item
    return result


def validate_sources(
    manifest: dict[str, Any],
    package: dict[str, Any],
    switchable: set[str],
) -> list[dict[str, str]]:
    """Valida fuentes sin tocar OpenDSS."""
    raw_sources = package.get("alternative_sources")
    if raw_sources is None:
        raw_sources = []
    if not isinstance(raw_sources, list):
        return [_issue("P12E001", "alternative_sources", "alternative_sources debe ser una lista explícita.")]

    buses = {
        str(item).strip()
        for item in (manifest.get("topology") or {}).get("buses") or []
        if str(item).strip()
    }
    issues: list[dict[str, str]] = []
    seen: set[str] = set()

    for i, item in enumerate(raw_sources):
        path = f"alternative_sources[{i}]"
        if not isinstance(item, dict):
            issues.append(_issue("P12E002", path, "Cada fuente alternativa debe ser un objeto estructurado."))
            continue

        identifier = normalize_source_id(item.get("id"))
        if not identifier:
            issues.append(_issue("P12E003", f"{path}.id", "La fuente alternativa requiere id."))
        elif not identifier.lower().startswith("vsource."):
            issues.append(_issue("P12E004", f"{path}.id", "P12E v1 requiere un identificador Vsource.*."))
        elif identifier.lower() == "vsource.source":
            issues.append(_issue("P12E005", f"{path}.id", "Vsource.source está reservado para la fuente principal."))
        elif identifier.lower() in seen:
            issues.append(_issue("P12E006", f"{path}.id", "No se permiten fuentes alternativas duplicadas."))
        else:
            seen.add(identifier.lower())

        if str(item.get("source_type") or "").strip().upper() != SOURCE_TYPE:
            issues.append(_issue(
                "P12E007",
                f"{path}.source_type",
                f"P12E v1 solo admite {SOURCE_TYPE}.",
            ))

        bus = str(item.get("bus") or "").strip()
        if not bus:
            issues.append(_issue("P12E008", f"{path}.bus", "La fuente requiere barra explícita."))
        elif bus not in buses:
            issues.append(_issue("P12E009", f"{path}.bus", "La barra de la fuente no existe en topology.buses."))

        phases = _number(item.get("phases"))
        if phases != 3:
            issues.append(_issue("P12E010", f"{path}.phases", "P12E v1 limita fuentes alternativas a 3 fases."))

        for key in ("kv_ll", "pu", "scc_mva", "x_r"):
            if not _positive(item.get(key)):
                issues.append(_issue("P12E011", f"{path}.{key}", f"{key} debe ser finito y mayor que cero."))

        angle = _number(item.get("angle_deg"))
        if angle is None:
            issues.append(_issue("P12E012", f"{path}.angle_deg", "angle_deg debe declararse explícitamente."))

        if not _present(item.get("source_reference")):
            issues.append(_issue("P12E013", f"{path}.source_reference", "La fuente requiere procedencia explícita."))

        isolation = item.get("required_isolation_elements")
        if not isinstance(isolation, list) or not isolation:
            issues.append(_issue(
                "P12E014",
                f"{path}.required_isolation_elements",
                "ENABLE_ALT_SOURCE requiere una lista no vacía de elementos de aislamiento.",
            ))
            isolation = []
        local_seen: set[str] = set()
        for j, element_raw in enumerate(isolation):
            epath = f"{path}.required_isolation_elements[{j}]"
            element = str(element_raw or "").strip()
            if not element:
                issues.append(_issue("P12E015", epath, "El elemento de aislamiento no puede estar vacío."))
            elif element not in switchable:
                issues.append(_issue(
                    "P12E016",
                    epath,
                    "El aislamiento debe referenciar Line.* o Transformer.* existente.",
                ))
            elif element.lower() in local_seen:
                issues.append(_issue("P12E017", epath, "Elemento de aislamiento duplicado."))
            else:
                local_seen.add(element.lower())

    return issues


def validate_source_action_sequence(
    scenario: dict[str, Any],
    package: dict[str, Any],
    *,
    scenario_index: int,
) -> list[dict[str, str]]:
    """Exige break-before-make para cada ENABLE_ALT_SOURCE."""
    sources = source_map(package)
    issues: list[dict[str, str]] = []
    explicitly_open: set[str] = set()

    for j, action in enumerate(scenario.get("actions") or []):
        if not isinstance(action, dict):
            continue
        apath = f"scenarios[{scenario_index}].actions[{j}]"
        kind = str(action.get("action") or "").strip().upper()
        element = str(action.get("element_id") or "").strip()

        if kind == "OPEN_ELEMENT" and element:
            explicitly_open.add(element.lower())
        elif kind == "CLOSE_ELEMENT" and element:
            explicitly_open.discard(element.lower())
        elif kind in ALLOWED_SOURCE_ACTIONS:
            source = sources.get(normalize_source_id(element).lower())
            if source is None:
                issues.append(_issue(
                    "P12E020",
                    f"{apath}.element_id",
                    "La acción referencia una fuente alternativa no declarada.",
                ))
                continue
            if kind == "ENABLE_ALT_SOURCE":
                missing = [
                    str(required)
                    for required in source.get("required_isolation_elements") or []
                    if str(required).lower() not in explicitly_open
                ]
                if missing:
                    issues.append(_issue(
                        "P12E021",
                        apath,
                        "Break-before-make incumplido: antes de ENABLE_ALT_SOURCE deben abrirse explícitamente: "
                        + ", ".join(missing) + ".",
                    ))
    return issues


def _source_name(identifier: str) -> str:
    return normalize_source_id(identifier).split(".", 1)[1]


def _equivalent(source: dict[str, Any]) -> dict[str, float]:
    kv_ll = float(source["kv_ll"])
    scc_mva = float(source["scc_mva"])
    x_r = float(source["x_r"])
    z1 = kv_ll * kv_ll / scc_mva
    r1 = z1 / sqrt(1.0 + x_r * x_r)
    x1 = r1 * x_r
    return {"z1_ohm": z1, "r1_ohm": r1, "x1_ohm": x1}


def materialize_sources(manifest: dict[str, Any], package: dict[str, Any]) -> list[dict[str, Any]]:
    """Crea Vsource alternativos deshabilitados sobre el modelo ya materializado."""
    frequency = float((manifest.get("source") or {}).get("frequency_hz"))
    created: list[dict[str, Any]] = []
    for item in package.get("alternative_sources") or []:
        identifier = normalize_source_id(item["id"])
        equivalent = _equivalent(item)
        dss(
            " ".join([
                f"New Vsource.{_source_name(identifier)}",
                f"Bus1={item['bus']}",
                "Phases=3",
                f"BasekV={float(item['kv_ll'])}",
                f"pu={float(item['pu'])}",
                f"angle={float(item['angle_deg'])}",
                f"Frequency={frequency}",
                f"R1={equivalent['r1_ohm']}",
                f"X1={equivalent['x1_ohm']}",
                "Enabled=No",
            ])
        )
        created.append({
            "id": identifier,
            "source_type": SOURCE_TYPE,
            "bus": str(item["bus"]),
            "frequency_hz": frequency,
            "positive_sequence_equivalent": equivalent,
            "zero_sequence_modeled": False,
            "initial_enabled": False,
            "source_reference": str(item["source_reference"]),
        })
    return created


def source_enabled_state(identifier: str) -> bool:
    source = normalize_source_id(identifier)
    dss(f"? {source}.enabled")
    raw = str(dss.Text.Result() or "").strip().lower()
    if raw in {"yes", "true", "1"}:
        return True
    if raw in {"no", "false", "0"}:
        return False
    raise ValueError(f"No se pudo leer Enabled para {source}: {raw!r}")


def set_source_enabled_state(identifier: str, *, enabled: bool) -> None:
    source = normalize_source_id(identifier)
    value = "Yes" if enabled else "No"
    dss(f"Edit {source} Enabled={value}")


def capture_action_state(action: dict[str, Any]) -> dict[str, Any]:
    return {
        "state_type": "ALT_SOURCE_ENABLED",
        "value": source_enabled_state(str(action["element_id"])),
    }


def apply_source_action(action: dict[str, Any]) -> dict[str, Any]:
    kind = str(action["action"]).upper()
    identifier = normalize_source_id(action["element_id"])
    requested = kind == "ENABLE_ALT_SOURCE"
    set_source_enabled_state(identifier, enabled=requested)
    return {
        "element_id": identifier,
        "action": kind,
        "effective_enabled_state": source_enabled_state(identifier),
        "source_reference": action["source_reference"],
        "break_before_make_contract": True,
    }


def restore_source_state(identifier: str, state: dict[str, Any]) -> None:
    set_source_enabled_state(identifier, enabled=bool(state["value"]))


def source_state_matches(identifier: str, state: dict[str, Any]) -> bool:
    return source_enabled_state(identifier) == bool(state["value"])
