"""QA determinístico del modelo antes de una emisión profesional.

No ejecuta estudios ni modifica los motores. Inspecciona el snapshot vigente,
las asignaciones trazables, los datos profesionales P2 y la matriz de madurez.
"""

from __future__ import annotations

from typing import Any

from . import conductor_library, validation_status, workspace_state

_ACCEPTABLE_FOR_EMISSION = {"VALIDATED_WITH_LIMITATIONS", "VALIDATED"}
_SHORT_CIRCUIT_STUDIES = {"short_circuit", "iec60909", "arc_flash_ieee1584", "protection_coordination"}


def _finding(code: str, severity: str, message: str, element: str | None = None) -> dict[str, Any]:
    return {"code": code, "severity": severity, "message": message, "element": element}


def auditar_modelo(estudios_requeridos: list[str] | None = None) -> dict[str, Any]:
    """Audita completitud y madurez sin afirmar cumplimiento normativo."""
    required = estudios_requeridos or ["power_flow", "voltage_drop"]
    needs_fault_data = bool(set(required) & _SHORT_CIRCUIT_STUDIES)
    model = workspace_state.collect_model_snapshot()
    assignments = conductor_library.snapshot_asignaciones().get("alimentadores", {})
    matrix = validation_status.get_validation_matrix()
    findings: list[dict[str, Any]] = []

    if not model.get("circuit"):
        findings.append(_finding("QA001", "BLOCKER", "No existe un circuito activo."))

    lines = model.get("lines", [])
    transformers = model.get("transformers", [])
    loads = model.get("loads", [])

    if not transformers:
        findings.append(_finding("QA010", "WARNING", "El modelo no contiene transformadores."))
    if not loads:
        findings.append(_finding("QA011", "WARNING", "El modelo no contiene cargas."))

    for line in lines:
        element = line["id"]
        if float(line.get("length") or 0) <= 0:
            findings.append(_finding("QA100", "ERROR", "Longitud de línea no positiva.", element))
        if float(line.get("r1") or 0) <= 0:
            findings.append(_finding("QA101", "ERROR", "R1 no positiva o no definida.", element))
        if float(line.get("x1") or 0) < 0:
            findings.append(_finding("QA102", "ERROR", "X1 negativa.", element))

        assignment = assignments.get(element.lower())
        visual_conductor = str(line.get("visual", {}).get("conductor") or "").strip()
        assignment_description = str((assignment or {}).get("descripcion") or "").strip()
        if assignment and assignment_description and visual_conductor != assignment_description:
            findings.append(_finding("QA112", "ERROR", "La asignación de conductor no coincide con el estado visual actual; puede ser un residuo de un modelo previo.", element))
            assignment = None
        if not assignment:
            findings.append(_finding("QA110", "WARNING", "El alimentador no tiene un conductor de biblioteca trazable asignado.", element))
        elif not assignment.get("fuente", {}).get("url"):
            findings.append(_finding("QA111", "ERROR", "Asignación de conductor sin URL de fuente.", element))

    for tr in transformers:
        element = tr["id"]
        windings = tr.get("windings", [])
        if len(windings) < 2:
            findings.append(_finding("QA200", "ERROR", "Transformador sin dos devanados legibles.", element))
        for winding in windings:
            if float(winding.get("kv") or 0) <= 0:
                findings.append(_finding("QA201", "ERROR", "Tensión de devanado no positiva.", element))
            if float(winding.get("kva") or 0) <= 0:
                findings.append(_finding("QA202", "ERROR", "Potencia de devanado no positiva.", element))

        p2 = tr.get("professional")
        if not p2:
            severity = "BLOCKER" if needs_fault_data else "WARNING"
            findings.append(_finding("QA210", severity, "Transformador sin ficha P2: %Z, X/R, grupo vectorial y procedencia no están documentados profesionalmente.", element))
            continue
        sc = p2.get("short_circuit", {})
        vg = p2.get("vector_group", {})
        if float(sc.get("uk_percent") or 0) <= 0:
            findings.append(_finding("QA211", "ERROR", "Transformador P2 sin uk/%Z válido.", element))
        if float(sc.get("x_r_effective") or 0) <= 0:
            findings.append(_finding("QA212", "ERROR", "Transformador P2 sin X/R efectivo válido.", element))
        if not vg.get("grupo_vectorial"):
            findings.append(_finding("QA213", "ERROR", "Transformador P2 sin grupo vectorial.", element))
        if not p2.get("provenance", {}).get("uk_percent", {}).get("reference"):
            findings.append(_finding("QA214", "ERROR", "Transformador P2 sin procedencia para uk/%Z.", element))
        if needs_fault_data and not p2.get("projection", {}).get("zero_sequence_ready"):
            findings.append(_finding("QA215", "BLOCKER", "El transformador no tiene todavía parámetros de secuencia cero suficientes para el estudio solicitado.", element))

    source = model.get("source")
    if needs_fault_data:
        if not source:
            findings.append(_finding("QA300", "BLOCKER", "El estudio solicitado requiere una red equivalente aguas arriba; la fuente sigue siendo ideal/no documentada."))
        else:
            active = source.get("scenarios", {}).get(source.get("active_scenario"))
            if not active or float(active.get("scc3_mva") or 0) <= 0 or float(active.get("x_r") or 0) <= 0:
                findings.append(_finding("QA301", "BLOCKER", "Escenario activo de red equivalente incompleto."))
            if not source.get("zero_sequence", {}).get("available"):
                findings.append(_finding("QA302", "BLOCKER", "La red equivalente no contiene Z0/MVAsc1; no es suficiente para fallas a tierra."))
    elif source and not source.get("provenance", {}).get("scc_max_mva", {}).get("reference"):
        findings.append(_finding("QA303", "WARNING", "Red equivalente definida sin referencia de procedencia."))

    module_checks = []
    for name in required:
        module = matrix.get(name)
        if module is None:
            module_checks.append({"module": name, "status": "UNKNOWN", "acceptable_for_emission": False})
            findings.append(_finding("QA900", "BLOCKER", f"Módulo requerido desconocido: {name}."))
            continue
        acceptable = module["status"] in _ACCEPTABLE_FOR_EMISSION
        module_checks.append({"module": name, "status": module["status"], "acceptable_for_emission": acceptable, "limitations": module.get("limitations", [])})
        if not acceptable:
            findings.append(_finding("QA901", "BLOCKER", f"El módulo {name} está en estado {module['status']} y aún no está habilitado para emisión profesional."))

    severity_order = {"INFO": 0, "WARNING": 1, "ERROR": 2, "BLOCKER": 3}
    findings.sort(key=lambda x: (-severity_order[x["severity"]], x["code"], x.get("element") or ""))
    blockers = sum(f["severity"] == "BLOCKER" for f in findings)
    errors = sum(f["severity"] == "ERROR" for f in findings)
    warnings = sum(f["severity"] == "WARNING" for f in findings)

    return {
        "circuit": model.get("circuit"),
        "estudios_requeridos": required,
        "module_checks": module_checks,
        "findings": findings,
        "summary": {
            "blockers": blockers,
            "errors": errors,
            "warnings": warnings,
            "model_data_ok": blockers == 0 and errors == 0,
            "apto_para_emision": blockers == 0 and errors == 0 and all(m["acceptable_for_emission"] for m in module_checks),
        },
        "nota": "La aptitud automática no sustituye la revisión ni responsabilidad del ingeniero responsable.",
    }
