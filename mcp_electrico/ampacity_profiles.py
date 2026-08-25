"""P3A — perfiles normativos de aplicabilidad para ampacidad.

Este módulo codifica *qué regla/factor se requiere*, no los valores numéricos
de tablas protegidas por copyright. Mantiene separados CNE Utilización 2006 e
IEC 60364-5-52:2009+AMD1:2024 para impedir mezclas silenciosas de edición.

Estados principales:
- RULE_SCHEMA_READY: la topología de reglas está modelada;
- REFERENCE_ONLY: solo existe la referencia normativa;
- TABLE_DATA_NOT_LOADED: la regla apunta a una tabla cuyo dataset no está cargado;
- MANUAL_REVIEW_REQUIRED: el alcance necesita interpretación/ramificación aún no automatizada.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

RULE_SCHEMA_READY = "RULE_SCHEMA_READY"
REFERENCE_ONLY = "REFERENCE_ONLY"
TABLE_DATA_NOT_LOADED = "TABLE_DATA_NOT_LOADED"
BASE_CONDITION = "BASE_CONDITION"
MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"

_CNE_SOURCE_URL = "https://spij.minjus.gob.pe/Graficos/Peru/2006/Enero/30/RM-037-2006.pdf"
_IEC_SOURCE_URL = "https://webstore.iec.ch/en/publication/103734"

_CNE_METHODS = {
    "A1": {"base_table": "Tabla 2", "environment_family": "air", "grouping_route": "Tabla 5C"},
    "A2": {"base_table": "Tabla 2", "environment_family": "air", "grouping_route": "Tabla 5C"},
    "B1": {"base_table": "Tabla 2", "environment_family": "air", "grouping_route": "Tabla 5C"},
    "B2": {"base_table": "Tabla 2", "environment_family": "air", "grouping_route": "Tabla 5C"},
    "C": {"base_table": "Tabla 2", "environment_family": "air", "grouping_route": "Tabla 5C"},
    "D": {"base_table": "Tabla 2", "environment_family": "buried", "grouping_route": "Tabla 5C"},
    "E": {"base_table": "Tabla 1", "environment_family": "air", "grouping_route": "Tabla 5C/5E según disposición"},
    "F": {"base_table": "Tabla 1", "environment_family": "air", "grouping_route": "Tabla 5C/5E según disposición"},
    "G": {"base_table": "Tabla 1", "environment_family": "air", "grouping_route": "Tabla 5C/5E según disposición"},
}

_PROFILES: dict[str, dict[str, Any]] = {
    "PERU_CNE_UTIL_2006_030_004": {
        "id": "PERU_CNE_UTIL_2006_030_004",
        "jurisdiction": "PE",
        "title": "CNE Utilización 2006 — Regla 030-004 Capacidad de Corriente",
        "status": RULE_SCHEMA_READY,
        "norm_reference_id": "PERU_CNE_UTILIZACION_2006",
        "scope": "conductores de utilización dentro del alcance declarado por Sección 030",
        "source": {
            "type": "official_legal_publication",
            "publisher": "Ministerio de Energía y Minas / SPIJ",
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
                "reference": "Regla 030-004(1)(c), (10) / Tablas 5C y ramas de Tabla 5E al aire",
                "dataset_status": TABLE_DATA_NOT_LOADED,
            },
            "mixed_installation_segments": {
                "reference": "Regla 030-004(13)-(14)",
                "policy": "LOWEST_AMPACITY_GOVERNS",
                "exception_14_automatic": False,
            },
        },
        "automatic_factor_lookup": False,
        "copyright_policy": "No se transcriben tablas completas; datasets numéricos se incorporarán solo con base legal/licencia y alcance versionado.",
    },
    "IEC_60364_5_52_2009_A1_2024": {
        "id": "IEC_60364_5_52_2009_A1_2024",
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
        "reason": "Referencia vigente registrada; dataset/tablas de Ed. 3.1 no cargados en MCP Eléctrico.",
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


def evaluar_aplicabilidad(
    profile_id: str,
    installation_method: str,
    environment: str | None = None,
    ambient_temperature_c: float | None = None,
    soil_thermal_resistivity_k_m_per_w: float | None = None,
    circuits_grouped: int = 1,
    grouping_arrangement: str | None = None,
    segment_count: int = 1,
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
            "profile": profile,
            "status": TABLE_DATA_NOT_LOADED,
            "automatic_factor_lookup": False,
            "applicable": False,
            "reason": "El perfil IEC 2024 está registrado solo como referencia; no se reutilizan tablas CNE 2006 bajo ese ID.",
            "required_axes": [],
            "missing_parameters": [],
            "manual_review": ["Cargar/autorizar dataset propio de la edición IEC seleccionada antes de resolver factores."],
        }

    method = _method(installation_method)
    method_info = deepcopy(_CNE_METHODS[method])
    base = profile["base_conditions"]
    missing: list[str] = []
    manual: list[str] = []
    axes: list[dict[str, Any]] = []

    env = str(environment or "").strip().lower()
    if method == "D":
        if env not in {"buried_duct", "direct_buried"}:
            missing.append("environment: buried_duct | direct_buried")
        temp_base = float(base["buried_duct_temperature_c"])
        temp_label = "enterrado"
    else:
        if env and env != "air":
            manual.append(f"Método {method}: environment={env} no coincide con la familia de instalación al aire del perfil P3A.")
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
                if changed else
                f"Temperatura {temp_label} coincide con condición base {temp_base:g} °C."
            ),
            TABLE_DATA_NOT_LOADED if changed else BASE_CONDITION,
        ))

    if method == "D":
        if env == "buried_duct":
            if soil_thermal_resistivity_k_m_per_w is None:
                missing.append("soil_thermal_resistivity_k_m_per_w")
            else:
                rho = float(soil_thermal_resistivity_k_m_per_w)
                if rho <= 0:
                    raise ValueError("P3P003: resistividad térmica del suelo debe ser positiva")
                rho_base = float(base["soil_thermal_resistivity_k_m_per_w"])
                changed = abs(rho - rho_base) > 1e-9
                axes.append(_axis(
                    "soil_thermal_resistivity",
                    changed,
                    "Regla 030-004(9) / Tabla 5B",
                    (
                        f"ρsuelo={rho:g} K·m/W difiere de base {rho_base:g} K·m/W."
                        if changed else
                        f"ρsuelo coincide con base {rho_base:g} K·m/W."
                    ),
                    TABLE_DATA_NOT_LOADED if changed else BASE_CONDITION,
                ))
        elif env == "direct_buried":
            manual.append(
                "P3A no automatiza corrección de resistividad para tendido directamente enterrado; "
                "la Regla 030-004(9) modelada se limita a método D en ductos enterrados."
            )

    grouped = int(circuits_grouped)
    if grouped < 1:
        raise ValueError("P3P004: circuits_grouped debe ser >= 1")
    if grouped > 1:
        if method in {"E", "F", "G"}:
            if not str(grouping_arrangement or "").strip():
                missing.append("grouping_arrangement")
            axes.append(_axis(
                "grouping",
                True,
                "Regla 030-004(1)(c), (10) / Tabla 5C o 5E según disposición",
                f"Se declararon {grouped} circuitos agrupados en método {method}; la rama exacta depende de la disposición física.",
                MANUAL_REVIEW_REQUIRED,
            ))
            manual.append("Definir disposición/bandeja/separación para elegir de forma inequívoca Tabla 5C o 5E.")
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
    segment_policy = {
        "segments": segments,
        "reference": "Regla 030-004(13)-(14)",
        "policy": "LOWEST_AMPACITY_GOVERNS" if segments > 1 else "SINGLE_SEGMENT",
        "exception_14_automatic": False,
    }
    if segments > 1:
        manual.append("Para múltiples condiciones de instalación, calcular cada tramo y usar la menor ampacidad según 030-004(13).")
    if request_short_segment_exception:
        manual.append(
            "La excepción de 030-004(14) (tramo corto de menor capacidad) no se automatiza en P3A; requiere revisión explícita."
        )
        segment_policy["exception_14_requested"] = True

    required_tables = sorted({item["reference"] for item in axes if item["required"]})
    unresolved = bool(
        missing
        or manual
        or any(item["status"] in {TABLE_DATA_NOT_LOADED, MANUAL_REVIEW_REQUIRED} for item in axes if item["required"])
    )

    return {
        "profile_id": profile["id"],
        "profile_status": profile["status"],
        "norm_reference_id": profile["norm_reference_id"],
        "installation_method": method,
        "base_ampacity_table": method_info["base_table"],
        "environment": env or None,
        "base_conditions": deepcopy(base),
        "required_axes": axes,
        "required_factor_tables": required_tables,
        "missing_parameters": missing,
        "manual_review": manual,
        "segment_policy": segment_policy,
        "automatic_factor_lookup": False,
        "can_auto_resolve_factors": False,
        "status": "REQUIREMENTS_IDENTIFIED" if not missing else "MISSING_INPUTS",
        "unresolved_numeric_factors": unresolved,
        "note": "P3A identifica reglas aplicables sin copiar ni devolver factores numéricos de tablas no cargadas.",
    }
