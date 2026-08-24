"""QA determinístico del modelo antes de una emisión profesional.

No ejecuta estudios ni modifica OpenDSS. Inspecciona el snapshot vigente,
las asignaciones trazables y la matriz de madurez técnica.
"""

from __future__ import annotations

from typing import Any

from . import conductor_library, validation_status, workspace_state

_ACCEPTABLE_FOR_EMISSION = {"VALIDATED_WITH_LIMITATIONS", "VALIDATED"}


def _finding(code: str, severity: str, message: str, element: str | None = None) -> dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "element": element,
    }


def auditar_modelo(estudios_requeridos: list[str] | None = None) -> dict[str, Any]:
    """Audita completitud y madurez sin afirmar cumplimiento normativo.

    ``apto_para_emision`` solo puede ser verdadero si:
    - no existen ERROR/BLOCKER de modelo;
    - todos los módulos solicitados tienen madurez aceptable para emisión.
    """
    required = estudios_requeridos or ["power_flow", "voltage_drop"]
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
        if not assignment:
            findings.append(
                _finding(
                    "QA110",
                    "WARNING",
                    "El alimentador no tiene un conductor de biblioteca trazable asignado.",
                    element,
                )
            )
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
        # El snapshot actual aún no expone %Z, X/R ni fuente. No se oculta esta brecha.
        findings.append(
            _finding(
                "QA210",
                "WARNING",
                "El snapshot profesional aún no documenta %Z, X/R y fuente del transformador.",
                element,
            )
        )

    module_checks = []
    for name in required:
        module = matrix.get(name)
        if module is None:
            module_checks.append({"module": name, "status": "UNKNOWN", "acceptable_for_emission": False})
            findings.append(_finding("QA900", "BLOCKER", f"Módulo requerido desconocido: {name}."))
            continue
        acceptable = module["status"] in _ACCEPTABLE_FOR_EMISSION
        module_checks.append({
            "module": name,
            "status": module["status"],
            "acceptable_for_emission": acceptable,
            "limitations": module.get("limitations", []),
        })
        if not acceptable:
            findings.append(
                _finding(
                    "QA901",
                    "BLOCKER",
                    f"El módulo {name} está en estado {module['status']} y aún no está habilitado para emisión profesional.",
                )
            )

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
