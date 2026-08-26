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
        "basis": "pandapower 3.5.x mediante puente explícito desde el modelo activo + datos P2",
        "limitations": [
            "Solo redes trifásicas balanceadas",
            "Líneas y cargas trifásicas; transformadores solo con ficha P2 suficiente",
            "No se traducen todavía generadores, motores ni redes desbalanceadas",
            "La fuente P2 se conserva para estudios de falla; el flujo pandapower usa ext_grid ideal a 1 pu",
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
    "ampacity": {
        "status": "VALIDATED_WITH_LIMITATIONS",
        "basis": (
            "P3-v1 CNE Utilización 2006: Ib/In/Iz + routing P3A + datasets PRIMARY_VERIFIED "
            "+ cobertura 5A/5B/5C/5D/5E + benchmarks primarios independientes P3C12"
        ),
        "limitations": [
            "El alcance validado corresponde a PERU_CNE_UTIL_2006_030_004 y no generaliza automáticamente a otras normas o ediciones",
            "Tablas 1/2 no están transcritas exhaustivamente: Iz_base profesional solo se resuelve para filas PRIMARY_VERIFIED con coincidencia exacta",
            "No se permite interpolación, extrapolación ni vecino más cercano en datasets normativos",
            "Cobertura primaria completa de una tabla no implica binding automático para toda combinación física; configuraciones no demostradas permanecen manuales o fail-closed",
            "Tabla 5A conserva fail-closed para columnas 20-25 por la inconsistencia editorial detectada entre el alcance literal de la tabla y el routing de Tabla 3",
            "Los datasets secundarios históricos permanecen disponibles solo con opt-in explícito y professional_emission=false",
            "IEC 60364-5-52:2009+AMD1:2024 permanece REFERENCE_ONLY hasta disponer de un dataset validado para esa edición",
            "La aptitud profesional de un modelo concreto depende además de sus datos, evidencia, QA y revisión del ingeniero responsable",
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
