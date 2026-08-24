"""Gate formal de cierre para la Fase P2.

P2 es una capacidad del producto, no un estado particular del circuito activo.
Por eso este módulo separa:

- ``phase``: si MCP Eléctrico ya implementó el contrato mínimo P2 v1;
- ``model``: coherencia del modelo activo respecto de ese contrato.

P2 v1 puede cerrarse con limitaciones aunque un modelo concreto tenga datos
faltantes. Eso no habilita P3/P4 para ese modelo: ``study_readiness`` y QA
siguen siendo las puertas por estudio.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from opendssdirect import dss

from . import conductor_library, professional_data, study_readiness, workspace_state, zero_sequence

PHASE_COMPLETE = "COMPLETE_WITH_LIMITATIONS"
PHASE_INCOMPLETE = "INCOMPLETE"
MODEL_READY = "MODEL_COHERENT"
MODEL_ISSUES = "MODEL_ISSUES"
NO_ACTIVE_MODEL = "NO_ACTIVE_MODEL"

# Contrato de producto P2 v1. Cada criterio corresponde a una capacidad real
# implementada y protegida por tests; no a la presencia de datos en un modelo
# particular.
P2_V1_CAPABILITIES: tuple[dict[str, Any], ...] = (
    {
        "id": "P2C01",
        "name": "transformer_professional_data",
        "status": "DONE",
        "evidence": "professional_data.agregar_transformador_profesional",
        "scope": "2 devanados, 3 fases, grupos Dd0/Yy0/Yyn0/Dyn1/Dyn11/Yd1/Yd11",
    },
    {
        "id": "P2C02",
        "name": "upstream_equivalent_max_min",
        "status": "DONE",
        "evidence": "professional_data.definir_red_equivalente",
        "scope": "Scc3/XR máximo y mínimo con escenario activo y procedencia",
    },
    {
        "id": "P2C03",
        "name": "traced_conductor_product_installation",
        "status": "DONE",
        "evidence": "conductor_library.aplicar_conductor",
        "scope": "producto de catálogo + instalación/condición publicada + procedencia; no Iz normativo",
    },
    {
        "id": "P2C04",
        "name": "explicit_zero_sequence",
        "status": "DONE",
        "evidence": "zero_sequence source/line/transformer canonical records",
        "scope": "R0/X0 explícitos para fuente/líneas y ficha Z0 canónica de transformador",
    },
    {
        "id": "P2C05",
        "name": "study_specific_readiness",
        "status": "DONE",
        "evidence": "study_readiness.evaluar",
        "scope": "READY_DATA/MISSING_DATA separado de ENGINE_NOT_READY/MODULE_NOT_READY",
    },
    {
        "id": "P2C06",
        "name": "workspace_v2_traceability",
        "status": "DONE",
        "evidence": "workspace inspector + workspace_p2_view",
        "scope": "fuente, transformador y cable/instalación con procedencia visible",
    },
    {
        "id": "P2C07",
        "name": "runtime_state_safety",
        "status": "DONE",
        "evidence": "runtime_safety + reset de estados P2",
        "scope": "sin reutilizar estado profesional o Z0 obsoleta al recrear/cambiar escenario",
    },
)

P2_V1_LIMITATIONS = [
    "La biblioteca de conductores es deliberadamente acotada y trazable; no pretende cubrir todo el mercado BT/MT.",
    "Los grupos vectoriales se limitan al subconjunto P2 v1 explícitamente soportado; configuraciones no soportadas se rechazan.",
    "R0/X0 no se infiere desde R1/X1 ni Scc3. La obtención desde geometría física queda como ampliación futura.",
    "La ficha Z0 del transformador es canónica y utilizable por una futura proyección pandapower, pero su proyección profesional a OpenDSS permanece bloqueada.",
    "La ampacidad publicada de catálogo no es Iz normativo; métodos de instalación y factores normativos pertenecen a P3.",
    "IEC 60909 no forma parte de P2; pertenece a P4 y sigue MODULE_NOT_READY.",
]


def _active_circuit() -> str:
    try:
        return str(dss.Circuit.Name() or "")
    except Exception:
        return ""


def _issue(code: str, severity: str, message: str, element: str | None = None) -> dict[str, Any]:
    return {"code": code, "severity": severity, "message": message, "element": element}


def _near(a: float, b: float, rel: float = 1e-6, abs_tol: float = 1e-6) -> bool:
    return abs(a - b) <= max(abs_tol, rel * max(abs(a), abs(b), 1.0))


def _source_checks(issues: list[dict[str, Any]]) -> None:
    source = professional_data.obtener_red_equivalente()
    if not source:
        return
    try:
        dss.Vsources.Name("source")
        engine_kv = float(dss.Vsources.BasekV())
    except Exception:
        issues.append(_issue("P2X101", "ERROR", "No se pudo verificar Vsource.source contra la red equivalente P2.", "Vsource.source"))
        return
    p2_kv = float(source.get("kv_ll") or 0)
    if p2_kv <= 0:
        issues.append(_issue("P2X102", "ERROR", "La red equivalente P2 no tiene tensión nominal positiva.", "Vsource.source"))
    elif not _near(engine_kv, p2_kv, rel=1e-5):
        issues.append(_issue(
            "P2X103",
            "ERROR",
            f"Tensión de red equivalente ({p2_kv} kV) no coincide con Vsource.source ({engine_kv} kV).",
            "Vsource.source",
        ))


def _line_checks(model: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    for line in model.get("lines", []):
        element = str(line.get("id") or "Line.?")
        phases = int(line.get("phases") or 0)
        if phases not in {1, 2, 3}:
            issues.append(_issue("P2X201", "ERROR", f"Número de fases no soportado/coherente: {phases}.", element))
        assignment = line.get("conductor_assignment")
        if assignment:
            expected = float(assignment.get("ampacidad_aplicada_a") or 0)
            try:
                dss.Lines.Name(str(line.get("name")))
                active_normamps = float(dss.Lines.NormAmps())
            except Exception:
                active_normamps = 0.0
            if expected > 0 and not _near(expected, active_normamps, rel=1e-6):
                issues.append(_issue(
                    "P2X202",
                    "ERROR",
                    f"NormAmps activo ({active_normamps} A) no coincide con la asignación trazable ({expected} A).",
                    element,
                ))
            if assignment.get("impedancia_actualizada"):
                ar = assignment.get("r1_aplicado_ohm_km")
                ax = assignment.get("x1_aplicado_ohm_km")
                if ar is not None and not _near(float(ar), float(line.get("r1") or 0), rel=1e-6):
                    issues.append(_issue("P2X203", "ERROR", "R1 activo no coincide con R1 trazable aplicado.", element))
                if ax is not None and not _near(float(ax), float(line.get("x1") or 0), rel=1e-6):
                    issues.append(_issue("P2X204", "ERROR", "X1 activo no coincide con X1 trazable aplicado.", element))


def _transformer_checks(model: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    for tr in model.get("transformers", []):
        p2 = tr.get("professional")
        if not p2:
            # Un transformador legado es permitido por el producto, pero no es
            # un modelo P2 profesional. Se reporta como WARNING de modelo.
            issues.append(_issue("P2X301", "WARNING", "Transformador legado sin ficha profesional P2.", str(tr.get("id"))))
            continue
        element = str(tr.get("id") or "Transformer.?")
        buses = tr.get("buses", [])
        expected_buses = p2.get("buses", {})
        if len(buses) >= 2:
            if str(buses[0]).lower() != str(expected_buses.get("hv") or "").lower():
                issues.append(_issue("P2X302", "ERROR", "Bus HV OpenDSS no coincide con ficha P2.", element))
            if str(buses[1]).lower() != str(expected_buses.get("lv") or "").lower():
                issues.append(_issue("P2X303", "ERROR", "Bus LV OpenDSS no coincide con ficha P2.", element))
        windings = tr.get("windings", [])
        rating = p2.get("rating", {})
        vg = p2.get("vector_group", {})
        expected = [
            (float(rating.get("kv_hv") or 0), float(rating.get("kva") or 0), vg.get("hv_connection")),
            (float(rating.get("kv_lv") or 0), float(rating.get("kva") or 0), vg.get("lv_connection")),
        ]
        for idx, (kv, kva, conn) in enumerate(expected):
            if idx >= len(windings):
                issues.append(_issue("P2X304", "ERROR", "Falta devanado esperado en OpenDSS.", element))
                continue
            w = windings[idx]
            if not _near(float(w.get("kv") or 0), kv, rel=1e-5):
                issues.append(_issue("P2X305", "ERROR", f"Tensión del devanado {idx+1} no coincide con ficha P2.", element))
            if not _near(float(w.get("kva") or 0), kva, rel=1e-5):
                issues.append(_issue("P2X306", "ERROR", f"kVA del devanado {idx+1} no coincide con ficha P2.", element))
            if str(w.get("connection") or "") != str(conn or ""):
                issues.append(_issue("P2X307", "ERROR", f"Conexión del devanado {idx+1} no coincide con grupo vectorial P2.", element))


def _load_generator_checks(model: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    bus_names = {str(bus.get("name") or "").lower() for bus in model.get("buses", [])}
    for kind in ("loads", "generators"):
        for item in model.get(kind, []):
            element = str(item.get("id") or "?")
            bus = str(item.get("bus") or "").lower()
            phases = int(item.get("phases") or 0)
            if bus and bus not in bus_names:
                issues.append(_issue("P2X401", "ERROR", "Elemento referencia un bus no presente en el snapshot.", element))
            if phases not in {1, 2, 3}:
                issues.append(_issue("P2X402", "ERROR", f"Número de fases no soportado/coherente: {phases}.", element))


def evaluar_modelo_actual() -> dict[str, Any]:
    """Evalúa coherencia P2 del circuito activo sin ejecutar estudios."""
    circuit = _active_circuit()
    if not circuit:
        return {
            "status": NO_ACTIVE_MODEL,
            "circuit": None,
            "issues": [],
            "summary": {"errors": 0, "warnings": 0},
        }
    model = workspace_state.collect_model_snapshot()
    issues: list[dict[str, Any]] = []
    _source_checks(issues)
    _line_checks(model, issues)
    _transformer_checks(model, issues)
    _load_generator_checks(model, issues)
    errors = sum(1 for item in issues if item["severity"] == "ERROR")
    warnings = sum(1 for item in issues if item["severity"] == "WARNING")
    return {
        "status": MODEL_READY if errors == 0 else MODEL_ISSUES,
        "circuit": circuit,
        "issues": issues,
        "summary": {"errors": errors, "warnings": warnings},
    }


def evaluar_cierre_p2() -> dict[str, Any]:
    """Devuelve el gate de producto P2 y, si existe, coherencia del modelo activo."""
    capabilities = [deepcopy(item) for item in P2_V1_CAPABILITIES]
    pending = [item for item in capabilities if item["status"] != "DONE"]
    phase_status = PHASE_COMPLETE if not pending else PHASE_INCOMPLETE
    return {
        "schema_version": 1,
        "phase": "P2",
        "phase_version": "P2-v1",
        "phase_status": phase_status,
        "ready_for_next_phase": phase_status == PHASE_COMPLETE,
        "capabilities": capabilities,
        "pending_capabilities": pending,
        "limitations": deepcopy(P2_V1_LIMITATIONS),
        "model": evaluar_modelo_actual(),
        "next_phase": "P3_ampacity" if phase_status == PHASE_COMPLETE else None,
        "note": (
            "El cierre P2 certifica la infraestructura/datos profesionales del producto dentro del alcance v1; "
            "cada modelo y estudio sigue sujeto a study_readiness, QA y madurez propia."
        ),
    }
