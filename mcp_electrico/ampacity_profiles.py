"""P3A — perfiles normativos de aplicabilidad para ampacidad.

Este módulo codifica *qué regla/factor se requiere*, no los valores numéricos
de tablas protegidas por copyright. Mantiene separados CNE Utilización 2006 e
IEC 60364-5-52:2009+AMD1:2024 para impedir mezclas silenciosas de edición.

P3A es un router normativo, no un motor de tablas. Identifica la tabla base,
los ejes de corrección que resultan aplicables y los datos que faltan. Los
factores numéricos permanecen sin resolver mientras no exista un dataset
versionado, autorizado y validado para la referencia exacta.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

RULE_SCHEMA_READY = "RULE_SCHEMA_READY"
REFERENCE_ONLY = "REFERENCE_ONLY"
TABLE_DATA_NOT_LOADED = "TABLE_DATA_NOT_LOADED"
BASE_CONDITION = "BASE_CONDITION"
MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
REQUIREMENTS_IDENTIFIED = "REQUIREMENTS_IDENTIFIED"
BASE_CONDITIONS_IDENTIFIED = "BASE_CONDITIONS_IDENTIFIED"
MISSING_INPUTS = "MISSING_INPUTS"

_CNE_SOURCE_URL = "https://www.gob.pe/institucion/minem/normas-legales/108855-0037-2006-mem"
_IEC_SOURCE_URL = "https://webstore.iec.ch/en/publication/103734"

_CNE_METHODS = {
    "A1": {"base_table": "Tabla 2", "environment_family": "air", "grouping_route": "Tabla 5C"},
    "A2": {"base_table": "Tabla 2", "environment_family": "air", "grouping_route": "Tabla 5C"},
    "B1": {"base_table": "Tabla 2", "environment_family": "air", "grouping_route": "Tabla 5C"},
    "B2": {"base_table": "Tabla 2", "environment_family": "air", "grouping_route": "Tabla 5C"},
    "C": {"base_table": "Tabla 2", "environment_family": "air", "grouping_route": "Tabla 5C"},
    "D": {"base_table": "Tabla 2", "environment_family": "buried", "grouping_route": "Tabla 5D"},
    "E": {"base_table": "Tabla 1", "environment_family": "air", "grouping_route": "Tabla 5C/5E según disposición"},
    "F": {"base_table": "Tabla 1", "environment_family": "air", "grouping_route": "Tabla 5C/5E según disposición"},
    "G": {"base_table": "Tabla 1", "environment_family": "air", "grouping_route": "Tabla 5C/5E según disposición"},
}

_PROFILES: dict[str, dict[str, Any]] = {
    "PERU_CNE_UTIL_2006_030_004": {
        "id": "PERU_CNE_UTIL_2006_030_004",
        "schema_version": 1,
        "jurisdiction": "PE",
        "title": "CNE Utilización 2006 — Regla 030-004 Capacidad de Corriente",
        "status": RULE_SCHEMA_READY,
        "norm_reference_id": "PERU_CNE_UTILIZACION_2006",
        "scope": "conductores de utilización dentro del alcance declarado por Sección 030",
        "source": {
            "type": "official_legal_publication",
            "publisher": "Ministerio de Energía y Minas del Perú",
            "reference": "R.M. N.° 0037-2006-MEM — CNE Utilización, Regla 030-004",
            "url": _CNE_SOURCE_URL,
        },
        "base_conditions": {
            "air_temperature_c": 30.0,
            "buried_duct_temperature_c": 20.0,
            "soil_thermal_resistivity_k_m_per_w": 2.5,
        },
        "installation_methods": deepcopy(_CNE_METHODS),
        "correction_rules": {
            "ambient_temperature": {
                "reference": "Regla 030-004(8) / Tabla 5A",
                "dataset_status": TABLE_DATA_NOT_LOADED,
            },
            "soil_thermal_resistivity": {
                "reference": "Regla 030-004(9) / Tabla 5B",
                "dataset_status": TABLE_DATA_NOT_LOADED,
                "scope": "método D, cables en ductos enterrados",
            },
            "grouping": {
                "reference": "Regla 030-004(1)(c), (10) / Tablas 5C, 5D y ramas 5E según instalación",
                "dataset_status": TABLE_DATA_NOT_LOADED,
            },
            "mixed_installation_segments": {
                "reference": "Regla 030-004(13)-(14)",
                "scope": "transición de una porción subterránea a otra visible",
                "policy": "LOWEST_AMPACITY_GOVERNS_WITHIN_RULE_13_SCOPE",
                "exception_14_automatic": False,
            },
        },
        "automatic_factor_lookup": False,
        "copyright_policy": (
            "No se transcriben tablas completas; datasets numéricos se incorporarán "
            "solo con base legal/licencia y alcance versionado."
        ),
    },
    "IEC_60364_5_52_2009_A1_2024": {
        "id": "IEC_60364_5_52_2009_A1_2024",
        "schema_version": 1,
        "jurisdiction": "INTERNATIONAL",
        "title": "IEC 60364-5-52:2009+AMD1:2024 — Ed. 3.1",
        "status": REFERENCE_ONLY,
        "norm_reference_id": "IEC_60364_5_52_2009_A1_2024",
        "scope": "low-voltage electrical installations — wiring systems",
        "source": {
            "type": "official_standard_catalog",
            "publisher": "IEC",
            "reference": "IEC 60364-5-52:2009+AMD1:2024, Edition 3.1",
            "url": _IEC_SOURCE_URL,
        },
        "automatic_factor_lookup": False,
        "reason": (
            "Referencia vigente registrada; dataset/tablas de Ed. 3.1 no cargados "
            "en MCP Eléctrico y no se reutilizan tablas CNE 2006 bajo este ID."
        ),
    },
}


def listar_perfiles() -> list[dict[str, Any]]:
    return [deepcopy(value) for _, value in sorted(_PROFILES.items())]


def obtener_perfil(profile_id: str) -> dict[str, Any]:
    key = str(profile_id or "").strip().upper()
    for profile in _PROFILES.values():
        if str(profile["id"]).upper() == key:
            return deepcopy(profile)
    raise ValueError(f"P3P001: perfil normativo no registrado: {profile_id}")


def validar_compatibilidad_norma(profile_id: str, norm_reference_id: str) -> dict[str, Any]:
    """Impide vincular un router de una edición con otra referencia normativa."""
    profile = obtener_perfil(profile_id)
    expected = str(profile.get("norm_reference_id") or "")
    actual = str(norm_reference_id or "").strip().upper()
    if expected.upper() != actual:
        raise ValueError(
            "P3P006: el perfil normativo y la referencia de cálculo no coinciden: "
            f"{profile['id']} requiere {expected}, no {norm_reference_id}"
        )
    return {
        "compatible": True,
        "profile_id": profile["id"],
        "norm_reference_id": expected,
    }


def _method(method: str) -> str:
    value = str(method or "").strip().upper()
    if value not in _CNE_METHODS:
        raise ValueError(
            "P3P002: método de instalación no soportado por el perfil CNE P3A; "
            "use A1, A2, B1, B2, C, D, E, F o G."
        )
    return value


def _axis(axis: str, required: bool, reference: str, reason: str, status: str) -> dict[str, Any]:
    return {
        "axis": axis,
        "required": bool(required),
        "reference": reference,
        "reason": reason,
        "status": status,
    }


def _segment_transition(value: str | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    normalized = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "underground_to_exposed": "underground_to_exposed",
        "subterraneo_a_visible": "underground_to_exposed",
        "subterráneo_a_visible": "underground_to_exposed",
        "other": "other",
        "otra": "other",
    }
    if normalized not in aliases:
        raise ValueError(
            "P3P007: segment_transition debe ser underground_to_exposed | other"
        )
    return aliases[normalized]


def evaluar_aplicabilidad(
    profile_id: str,
    installation_method: str,
    environment: str | None = None,
    ambient_temperature_c: float | None = None,
    soil_thermal_resistivity_k_m_per_w: float | None = None,
    burial_depth_m: float | None = None,
    circuits_grouped: int = 1,
    grouping_arrangement: str | None = None,
    segment_count: int = 1,
    segment_transition: str | None = None,
    request_short_segment_exception: bool = False,
) -> dict[str, Any]:
    """Determina tablas/ejes requeridos sin devolver factores numéricos.

    El resultado es deliberadamente un *router normativo*. Cuando una tabla es
    necesaria, su estado permanece TABLE_DATA_NOT_LOADED hasta que exista un
    dataset autorizado y benchmarkeado para ese perfil exacto.
    """
    profile = obtener_perfil(profile_id)
    if profile["id"] != "PERU_CNE_UTIL_2006_030_004":
        return {
            "profile_id": profile["id"],
            "profile_status": profile["status"],
            "norm_reference_id": profile["norm_reference_id"],
            "status": TABLE_DATA_NOT_LOADED,
            "automatic_factor_lookup": False,
            "applicable": False,
            "reason": (
                "El perfil IEC 2024 está registrado solo como referencia; "
                "no se reutilizan tablas CNE 2006 bajo ese ID."
            ),
            "required_axes": [],
            "required_factor_tables": [],
            "missing_parameters": [],
            "manual_review": [
                "Cargar/autorizar dataset propio de la edición IEC seleccionada antes de resolver factores."
            ],
            "can_auto_resolve_factors": False,
            "unresolved_numeric_factors": True,
        }

    method = _method(installation_method)
    method_info = deepcopy(_CNE_METHODS[method])
    base = profile["base_conditions"]
    missing: list[str] = []
    manual: list[str] = []
    axes: list[dict[str, Any]] = []
    depth: float | None = None

    env_raw = str(environment or "").strip().lower()
    if method == "D":
        if env_raw not in {"buried_duct", "direct_buried"}:
            missing.append("environment: buried_duct | direct_buried")
            env = env_raw or None
        else:
            env = env_raw
        temp_base = float(base["buried_duct_temperature_c"])
        temp_label = "tierra/ducto enterrado"
    else:
        env = "air"
        if env_raw and env_raw != "air":
            manual.append(
                f"Método {method}: environment={env_raw} no coincide con la familia al aire del perfil P3A."
            )
        temp_base = float(base["air_temperature_c"])
        temp_label = "aire"

    if ambient_temperature_c is None:
        missing.append("ambient_temperature_c")
    else:
        actual_temp = float(ambient_temperature_c)
        changed = abs(actual_temp - temp_base) > 1e-9
        axes.append(_axis(
            "ambient_temperature",
            changed,
            "Regla 030-004(8) / Tabla 5A",
            (
                f"Temperatura {temp_label} {actual_temp:g} °C difiere de condición base {temp_base:g} °C."
                if changed
                else f"Temperatura {temp_label} coincide con condición base {temp_base:g} °C."
            ),
            TABLE_DATA_NOT_LOADED if changed else BASE_CONDITION,
        ))

    if method == "D":
        if burial_depth_m is not None:
            depth = float(burial_depth_m)
            if depth <= 0:
                raise ValueError("P3P008: profundidad de enterramiento debe ser positiva")

        if env == "buried_duct":
            if soil_thermal_resistivity_k_m_per_w is None:
                missing.append("soil_thermal_resistivity_k_m_per_w")
            else:
                rho = float(soil_thermal_resistivity_k_m_per_w)
                if rho <= 0:
                    raise ValueError("P3P003: resistividad térmica del suelo debe ser positiva")
                rho_base = float(base["soil_thermal_resistivity_k_m_per_w"])
                changed = abs(rho - rho_base) > 1e-9
                axis_status = BASE_CONDITION
                detail = f"ρsuelo coincide con base {rho_base:g} K·m/W."
                if changed:
                    if depth is None:
                        missing.append("burial_depth_m")
                        axis_status = TABLE_DATA_NOT_LOADED
                    elif depth <= 0.8 + 1e-12:
                        axis_status = TABLE_DATA_NOT_LOADED
                    else:
                        axis_status = MANUAL_REVIEW_REQUIRED
                        manual.append(
                            f"Tabla 5B limita sus factores a ductos hasta 0,8 m; profundidad declarada={depth:g} m. "
                            "No se extrapola automáticamente; use revisión de ingeniería/IEC 60287."
                        )
                    detail = (
                        f"ρsuelo={rho:g} K·m/W difiere de base {rho_base:g} K·m/W; "
                        + (f"profundidad={depth:g} m." if depth is not None else "falta profundidad de enterramiento.")
                    )
                axes.append(_axis(
                    "soil_thermal_resistivity",
                    changed,
                    "Regla 030-004(9) / Tabla 5B",
                    detail,
                    axis_status,
                ))
        elif env == "direct_buried":
            manual.append(
                "P3A no extrapola la Tabla 5B a tendido directamente enterrado; "
                "la rama automatizada de 030-004(9) se limita a conductores en ductos enterrados."
            )

    grouped = int(circuits_grouped)
    if grouped < 1:
        raise ValueError("P3P004: circuits_grouped debe ser >= 1")
    arrangement = str(grouping_arrangement or "").strip() or None
    if grouped > 1:
        if method == "D":
            if not arrangement:
                missing.append("grouping_arrangement")
            axes.append(_axis(
                "grouping",
                True,
                "Tabla 5D — factores de reducción para más de un circuito en ductos enterrados",
                (
                    f"Se declararon {grouped} circuitos para método D; la Tabla 5D depende de la disposición "
                    "y separación física de cables/ductos."
                ),
                MANUAL_REVIEW_REQUIRED,
            ))
            manual.append(
                "P3A identifica Tabla 5D para método D, pero todavía no clasifica automáticamente sus ramas "
                "por cable/ducto y separación; se requiere disposición explícita antes del lookup numérico."
            )
        elif method in {"E", "F", "G"}:
            if not arrangement:
                missing.append("grouping_arrangement")
            axes.append(_axis(
                "grouping",
                True,
                "Regla 030-004(1)(c), (10) / Tabla 5C o 5E según disposición",
                (
                    f"Se declararon {grouped} circuitos agrupados en método {method}; "
                    "la rama exacta depende de la disposición física."
                ),
                MANUAL_REVIEW_REQUIRED,
            ))
            manual.append(
                "P3A todavía no clasifica automáticamente la disposición de E/F/G entre las ramas 5C/5E; "
                "debe revisarse la configuración física declarada."
            )
        else:
            axes.append(_axis(
                "grouping",
                True,
                "Regla 030-004(1)(c), (10) / Tabla 5C",
                f"Se declararon {grouped} circuitos agrupados.",
                TABLE_DATA_NOT_LOADED,
            ))
    else:
        axes.append(_axis(
            "grouping",
            False,
            "Regla 030-004(1)(c), (10)",
            "Un solo circuito declarado; no se solicita factor de agrupamiento en P3A.",
            BASE_CONDITION,
        ))

    segments = int(segment_count)
    if segments < 1:
        raise ValueError("P3P005: segment_count debe ser >= 1")
    transition = _segment_transition(segment_transition)
    segment_policy: dict[str, Any] = {
        "segments": segments,
        "transition": transition,
        "reference": "Regla 030-004(13)-(14)",
        "rule_13_scope": "transición de una porción subterránea a otra visible",
        "exception_14_automatic": False,
    }
    if segments == 1:
        segment_policy["policy"] = "SINGLE_SEGMENT"
    elif transition is None:
        missing.append("segment_transition: underground_to_exposed | other")
        segment_policy["policy"] = MANUAL_REVIEW_REQUIRED
    elif transition == "underground_to_exposed":
        segment_policy["policy"] = "LOWEST_AMPACITY_GOVERNS"
        manual.append(
            "Regla 030-004(13): determinar la ampacidad aplicable a cada porción subterránea/visible y gobernar por la menor."
        )
    else:
        segment_policy["policy"] = MANUAL_REVIEW_REQUIRED
        manual.append(
            "030-004(13) no se generaliza a cualquier cambio de condición; la transición declarada queda para revisión de ingeniería."
        )

    if request_short_segment_exception:
        segment_policy["exception_14_requested"] = True
        manual.append(
            "La excepción de 030-004(14) no se automatiza en P3A. Debe verificarse manualmente su alcance, "
            "incluyendo número de conductores y longitud del tramo de menor ampacidad."
        )

    required_tables = sorted({item["reference"] for item in axes if item["required"]})
    numeric_unresolved = any(
        item["required"] and item["status"] in {TABLE_DATA_NOT_LOADED, MANUAL_REVIEW_REQUIRED}
        for item in axes
    )

    if missing:
        status = MISSING_INPUTS
    elif manual:
        status = MANUAL_REVIEW_REQUIRED
    elif numeric_unresolved:
        status = REQUIREMENTS_IDENTIFIED
    else:
        status = BASE_CONDITIONS_IDENTIFIED

    return {
        "profile_id": profile["id"],
        "profile_status": profile["status"],
        "norm_reference_id": profile["norm_reference_id"],
        "installation_method": method,
        "base_ampacity_table": method_info["base_table"],
        "environment": env,
        "burial_context": {
            "burial_depth_m": depth,
            "table_5b_max_automatic_depth_m": 0.8 if method == "D" and env == "buried_duct" else None,
        },
        "base_conditions": deepcopy(base),
        "grouping_context": {
            "circuits_grouped": grouped,
            "arrangement": arrangement,
            "route": method_info["grouping_route"],
        },
        "required_axes": axes,
        "required_factor_tables": required_tables,
        "missing_parameters": missing,
        "manual_review": manual,
        "segment_policy": segment_policy,
        "automatic_factor_lookup": False,
        "can_auto_resolve_factors": False,
        "status": status,
        "applicable": True,
        "unresolved_numeric_factors": numeric_unresolved,
        "note": (
            "P3A identifica reglas aplicables sin copiar ni devolver factores numéricos de tablas no cargadas."
        ),
    }
