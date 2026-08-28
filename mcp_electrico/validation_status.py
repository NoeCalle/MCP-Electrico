"""Estado de madurez técnica por módulo.

Esta matriz no reemplaza la revisión profesional. Expone de forma explícita
qué partes del sistema están validadas, en validación o no implementadas.

IEC 60909 tiene una madurez independiente del FaultStudy exploratorio de
OpenDSS. Su estado se resuelve de forma perezosa desde ``iec60909_maturity``
para evitar que una promoción P4 valide accidentalmente todo cortocircuito.
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
        "basis": "OpenDSS FaultStudy exploratorio",
        "limitations": [
            "No constituye el módulo IEC 60909 P4-v1",
            "La madurez IEC 60909 se registra por separado y no se hereda a FaultStudy",
        ],
    },
    "protection_data": {
        "status": "EXPERIMENTAL",
        "basis": "P5A_PROTECTION_DATA_CONTRACT_V1: dispositivos, ratings, ajustes explícitos y procedencia",
        "limitations": [
            "P5A cubre interruptores y fusibles; relés quedan fuera hasta modelar CT/VT, funciones y elemento de corte",
            "No existen todavía datasets numéricos TCC ni evaluación de tiempos de despeje",
            "No se sintetizan curvas de fabricante ni ajustes ausentes",
            "In P5A se contrasta con P3 cuando existe, pero nunca se crea automáticamente desde P3",
            "tk_s de P4 no se interpreta como tiempo real de despeje",
            "professional_emission=false",
        ],
    },
    "protection_coordination": {
        "status": "NOT_IMPLEMENTED",
        "basis": "P5A inició el contrato de datos; motor TCC/coordinación aún no implementado",
        "limitations": [
            "Curvas TCC numéricas, tiempos de despeje, selectividad y backup pendientes",
            "La existencia de datos P5A no habilita coordinación profesional",
        ],
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


def _iec60909_status() -> dict:
    from . import iec60909_maturity

    status = iec60909_maturity.get_validation_status()
    if status.get("status") not in VALID_STATES:
        raise ValueError(f"Estado IEC 60909 inválido: {status.get('status')}")
    return status


def get_validation_matrix() -> dict:
    modules = deepcopy(_MODULES)
    modules["iec60909"] = _iec60909_status()
    return modules


def get_module_status(name: str) -> dict:
    if name == "iec60909":
        return deepcopy(_iec60909_status())
    if name not in _MODULES:
        raise KeyError(f"Módulo desconocido: {name}")
    return deepcopy(_MODULES[name])
