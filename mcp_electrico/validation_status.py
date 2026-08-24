"""Estado de madurez técnica por módulo.

Esta matriz no reemplaza la revisión profesional. Expone de forma explícita
qué partes del sistema están validadas, en validación o no implementadas.
"""

from __future__ import annotations

from copy import deepcopy

VALID_STATES = {
    "NOT_IMPLEMENTED",
    "EXPERIMENTAL",
    "UNDER_VALIDATION",
    "VALIDATED_WITH_LIMITATIONS",
    "VALIDATED",
}

_MODULES = {
    "power_flow": {
        "status": "VALIDATED_WITH_LIMITATIONS",
        "basis": "OpenDSS + postproceso MCP + benchmarks P1 independientes",
        "limitations": [
            "Validado cuantitativamente en casos radiales trifásicos balanceados de dos barras con carga PQ",
            "Benchmarks IEEE/EPRI de alimentadores completos todavía pendientes",
            "Cobertura desbalanceada y equipos de regulación todavía no incluida en P1",
        ],
    },
    "voltage_drop": {
        "status": "VALIDATED_WITH_LIMITATIONS",
        "basis": "Tensiones pu OpenDSS + comparación P1 contra solución independiente",
        "limitations": [
            "Validación P1 limitada a caída por objeto Line en redes radiales balanceadas",
            "Caída acumulada hasta cargas y alimentadores desbalanceados todavía no benchmarkeada",
            "El límite porcentual de aceptación continúa siendo criterio configurable del usuario",
        ],
    },
    "pandapower_power_flow": {
        "status": "EXPERIMENTAL",
        "basis": "pandapower 3.5.x mediante puente explícito desde el modelo activo",
        "limitations": [
            "Solo redes trifásicas balanceadas de un único nivel de tensión",
            "Solo elementos Line + Load con fuente ideal en sourcebus",
            "Transformadores, generadores, motores y redes desbalanceadas se rechazan en v1",
            "No existe todavía router automático ni cross-check entre motores",
        ],
    },
    "conductor_library": {
        "status": "VALIDATED_WITH_LIMITATIONS",
        "basis": "Fichas Nexans/INDECO Perú trazables",
        "limitations": [
            "Catálogo inicial reducido",
            "BT no reemplaza R1/X1 si falta X de fuente primaria",
            "R0/X0 y geometrías avanzadas pendientes",
        ],
    },
    "short_circuit": {
        "status": "UNDER_VALIDATION",
        "basis": "OpenDSS FaultStudy",
        "limitations": ["No constituye todavía un motor IEC 60909 formal"],
    },
    "protection_coordination": {
        "status": "NOT_IMPLEMENTED",
        "basis": None,
        "limitations": ["Curvas TCC comerciales y coordinación pendientes"],
    },
    "arc_flash_ieee1584": {
        "status": "NOT_IMPLEMENTED",
        "basis": None,
        "limitations": ["IEEE 1584-2018 no implementado"],
    },
    "arc_flash_lee": {
        "status": "EXPERIMENTAL",
        "basis": "Método simplificado de Lee",
        "limitations": ["No sustituye IEEE 1584"],
    },
    "professional_report": {
        "status": "NOT_IMPLEMENTED",
        "basis": None,
        "limitations": ["Expediente reproducible y hash de emisión pendientes"],
    },
}


def get_validation_matrix() -> dict:
    return deepcopy(_MODULES)


def get_module_status(name: str) -> dict:
    if name not in _MODULES:
        raise KeyError(f"Módulo desconocido: {name}")
    return deepcopy(_MODULES[name])
