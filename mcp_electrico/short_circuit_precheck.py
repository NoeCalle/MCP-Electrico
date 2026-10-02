"""Read-only review gate for the public 3F source-equivalent study.

Numerical compatibility is not evidence that a model represents a real plant.
No missing machine/cable data are guessed and no electrical solve is performed
by the precheck. An acknowledgement binds the review to the actual inputs.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any

from opendssdirect import dss

from . import iec60909, pandapower_engine

SCOPE = "APORTE_FUENTES_EQUIVALENTES"
REVIEW_ITEMS = {
    "ORIGEN_DATOS": "Confirmar qué entradas son verificadas y cuáles son supuestas, con sus referencias.",
    "CABLES_REALES": "Revisar longitudes, R/X, conexiones y temperaturas; las entradas no acreditan por sí solas cables reales.",
    "APORTE_MOTORES": "Los elementos Load no aportan corriente de motor en este adaptador. MW/fp no identifican el tipo de carga ni justifican omitir motores.",
    "GENERADOR_SINCRONO": "La fuente se proyecta como equivalente ext_grid. No se modelan generador síncrono IEC, decaimiento ni correcciones de unidad generador-transformador.",
    "PROTECCIONES": "Este cálculo no valida interruptores/relés: faltan evaluación por rama, fichas, curvas, ajustes y tiempos reales según el objetivo.",
}
QUALITY = {"REALES_DECLARADOS", "SUPUESTOS_APROBADOS", "MIXTOS"}


def evaluar(
    bus_falla: str,
    line_endtemp_degree_c: dict[str, float] | None = None,
    calcular_ip_ith: bool = False,
    topology: str | None = None,
    tk_s: float | None = None,
    kappa_method: str = "C",
) -> dict[str, Any]:
    """Expose numerical readiness and a separate physical-model checklist."""
    kwargs = dict(line_endtemp_degree_c=line_endtemp_degree_c,
                  calcular_ip_ith=calcular_ip_ith, topology=topology,
                  tk_s=tk_s, kappa_method=kappa_method)
    readiness = {case: iec60909.evaluar_preparacion_3ph(case, bus_falla, **kwargs)
                 for case in ("max", "min")}
    model = pandapower_engine._collect_active_model()
    unsupported = []
    for full in dss.Circuit.AllElementNames() if model["circuit"] else []:
        element_class = full.split(".")[0].lower()
        if (element_class in {"generator", "indmach012", "pvsystem", "storage"}
                or element_class == "vsource" and full.lower() != "vsource.source"):
            dss.Circuit.SetActiveElement(full)
            if dss.CktElement.Enabled():
                unsupported.append(full)
    model["untranslated_fault_sources"] = unsupported
    request = {"bus_falla": bus_falla, **kwargs}
    encoded = json.dumps({"model": model, "request": request},
                         sort_keys=True, ensure_ascii=False, allow_nan=False,
                         separators=(",", ":")).encode("utf-8")
    fingerprint = sha256(encoded).hexdigest()
    near_ideal = [line["id"] for line in model["lines"]
                  if abs(line["length_km"] * line["r1_ohm_km"]) <= 1e-5
                  and abs(line["length_km"] * line["x1_ohm_km"]) <= 1e-5]
    return {
        "schema": "MCP_ELECTRICO_SC3_MODEL_PRECHECK_V1",
        "execution_status": "REQUIERE_REVISION_PREVIA",
        "numerical_ready": not unsupported and all(item["ready"] for item in readiness.values()),
        "numeric_readiness": readiness,
        "model_sha256": fingerprint,
        "supported_scope": SCOPE,
        "protection_validation_supported": False,
        "physical_completeness_verified": False,
        "missing_from_diagram_detection": False,
        "notice": (
            "Tener números suficientes para resolver no demuestra un modelo real completo. "
            "Revisar estas entradas y comunicar faltantes/supuestos ANTES de ejecutar. "
            "El MCP no puede descubrir equipos omitidos de un plano que no fue incorporado al modelo."
        ),
        "items_to_review": [{"id": key, "message": value} for key, value in REVIEW_ITEMS.items()],
        "input_inventory": {
            "source": deepcopy(model["source"]),
            "lines": deepcopy(model["lines"]),
            "transformers": deepcopy(model["transformers"]),
            "loads_without_motor_fault_model": deepcopy(model["loads"]),
            "generators_unsupported_by_adapter": deepcopy(model["generators"]),
            "untranslated_fault_sources": unsupported,
            "near_ideal_links_to_confirm": near_ideal,
            "system_frequency_hz": model.get("frequency_hz"),
        },
        "request": request,
        "required_review": {
            "model_sha256": fingerprint,
            "uso_previsto": SCOPE,
            "calidad_datos": "REALES_DECLARADOS | SUPUESTOS_APROBADOS | MIXTOS",
            "referencia_revision": "Referencia explícita a la revisión y aceptación del alcance/supuestos.",
            "supuestos_aprobados": ["Detalle de cada supuesto aprobado; obligatorio para datos supuestos o mixtos."],
            "exclusiones_revisadas": list(REVIEW_ITEMS),
        },
        "professional_emission": False,
    }


def validar_revision(precheck: dict[str, Any], revision_modelo: dict | None) -> list[dict]:
    """Reject absent/stale/ambiguous acceptance without calling a solver."""
    issues = []
    def add(code, message):
        issues.append({"code": code, "message": message})
    if not precheck["numerical_ready"]:
        add("SCREV001", "Hay datos numéricos faltantes o fuera de alcance; revisar numeric_readiness MAX/MIN.")
    if not isinstance(revision_modelo, dict):
        add("SCREV002", "Falta revisión previa. Presentar faltantes, supuestos y exclusiones antes de ejecutar.")
        return issues
    if revision_modelo.get("model_sha256") != precheck["model_sha256"]:
        add("SCREV003", "La revisión no corresponde al modelo y solicitud actuales. Obtener un nuevo control previo después de cambiar entradas, maniobras, barra de falla o parámetros del estudio.")
    if revision_modelo.get("uso_previsto") != SCOPE:
        add("SCREV004", "Este adaptador solo calcula APORTE_FUENTES_EQUIVALENTES; no comprueba protecciones ni incorpora aportes de máquinas omitidas.")
    quality = revision_modelo.get("calidad_datos")
    if not isinstance(quality, str) or quality not in QUALITY:
        add("SCREV005", "Declarar calidad_datos: REALES_DECLARADOS, SUPUESTOS_APROBADOS o MIXTOS.")
    ref = revision_modelo.get("referencia_revision")
    if not isinstance(ref, str) or not ref.strip():
        add("SCREV006", "Falta referencia explícita a la revisión del modelo y aprobación del alcance/supuestos.")
    exclusions = revision_modelo.get("exclusiones_revisadas")
    if (not isinstance(exclusions, list) or
            not all(isinstance(item, str) for item in exclusions) or
            not set(REVIEW_ITEMS).issubset(set(exclusions))):
        add("SCREV007", "Revisar todas las exclusiones y cuestiones de completitud que devuelve items_to_review.")
    assumed = revision_modelo.get("supuestos_aprobados")
    if isinstance(quality, str) and quality in {"SUPUESTOS_APROBADOS", "MIXTOS"}:
        if (not isinstance(assumed, list) or not assumed or
                not all(isinstance(item, str) and item.strip() for item in assumed)):
            add("SCREV008", "Detallar los supuestos aprobados; una etiqueta de datos supuestos no reemplaza su revisión.")
    return issues


def ejecutar_revisado(
    bus_falla: str,
    line_endtemp_degree_c: dict[str, float] | None = None,
    calcular_ip_ith: bool = False,
    topology: str | None = None,
    tk_s: float | None = None,
    kappa_method: str = "C",
    revision_modelo: dict | None = None,
) -> dict[str, Any]:
    """Public execution gate; results remain source-equivalent and partial."""
    from . import iec60909_suite

    precheck = evaluar(bus_falla, line_endtemp_degree_c, calcular_ip_ith,
                       topology, tk_s, kappa_method)
    issues = validar_revision(precheck, revision_modelo)
    if issues:
        return {
            "schema": "MCP_ELECTRICO_SC3_REVIEW_BLOCKED_V1",
            "ok": False, "resultados_validos": False,
            "study": "iec60909", "fault": "3ph", "bus": bus_falla,
            "execution_status": "BLOQUEADO_ANTES_DEL_CALCULO",
            "electrical_calculation_executed": False,
            "issues": issues, "model_precheck": precheck,
            "protection_validation_supported": False,
            "professional_emission": False,
        }
    result = iec60909_suite.ejecutar_3ph_max_min(
        bus_falla, line_endtemp_degree_c, calcular_ip_ith,
        topology, tk_s, kappa_method,
    )
    return {
        **result,
        "execution_status": "CALCULADO_APORTE_PARCIAL" if result["ok"] else "ERROR_NUMERICO",
        "electrical_calculation_executed": True,
        "engineering_status": "PARCIAL_NO_VALIDA_PROTECCIONES",
        "result_scope": SCOPE,
        "physical_completeness_verified": False,
        "protection_validation_supported": False,
        "model_precheck": precheck,
        "model_review": deepcopy(revision_modelo),
        "professional_emission": False,
    }
