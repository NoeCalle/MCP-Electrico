"""Metadatos visuales del unifilar que no alteran el cálculo OpenDSS.

Este módulo guarda únicamente decisiones de representación: si una carga debe
verse como motor/tablero y qué dispositivos gráficos (ATS/UPS) se intercalan en
un alimentador. No modifica impedancias, topología ni resultados eléctricos.
"""

from __future__ import annotations

from copy import deepcopy

from opendssdirect import dss

VALID_LOAD_TYPES = {"tablero", "motor", "carga"}
VALID_INLINE_DEVICES = {"ats", "ups"}

_load_types: dict[str, str] = {}
_feeders: dict[str, dict] = {}
_circuit_name: str | None = None


def _active_circuit_name() -> str:
    try:
        return str(dss.Circuit.Name() or "")
    except Exception:
        return ""


def _sync_circuit() -> None:
    global _circuit_name
    current = _active_circuit_name()
    if current != _circuit_name:
        _load_types.clear()
        _feeders.clear()
        _circuit_name = current


def reset() -> None:
    global _circuit_name
    _load_types.clear()
    _feeders.clear()
    _circuit_name = _active_circuit_name()


def set_load_type(nombre_carga: str, tipo_visual: str) -> dict:
    _sync_circuit()
    tipo = tipo_visual.strip().lower()
    if tipo not in VALID_LOAD_TYPES:
        admitidos = ", ".join(sorted(VALID_LOAD_TYPES))
        raise ValueError(f"tipo_visual no válido: {tipo_visual}. Admitidos: {admitidos}.")
    disponibles = {n.lower() for n in dss.Loads.AllNames()}
    if nombre_carga.lower() not in disponibles:
        raise ValueError(f"Carga no encontrada en el circuito: {nombre_carga}")
    _load_types[nombre_carga.lower()] = tipo
    return {"carga": nombre_carga, "tipo_visual": tipo}


def get_load_type(nombre_carga: str) -> str:
    _sync_circuit()
    return _load_types.get(nombre_carga.lower(), "tablero")


def configure_feeder(
    nombre_elemento: str,
    etiqueta: str = "",
    dispositivos: list[str] | None = None,
    fuente_alterna: str | None = None,
) -> dict:
    _sync_circuit()
    if not dss.Circuit.SetActiveElement(nombre_elemento):
        raise ValueError(f"Elemento no encontrado en el circuito: {nombre_elemento}")

    devices = [d.strip().lower() for d in (dispositivos or [])]
    invalidos = sorted(set(devices) - VALID_INLINE_DEVICES)
    if invalidos:
        admitidos = ", ".join(sorted(VALID_INLINE_DEVICES))
        raise ValueError(
            f"Dispositivos visuales no válidos: {', '.join(invalidos)}. "
            f"Admitidos: {admitidos}."
        )

    alternate = fuente_alterna.strip() if fuente_alterna else None
    if alternate:
        if "." not in alternate:
            alternate = f"Generator.{alternate}"
        if not dss.Circuit.SetActiveElement(alternate):
            raise ValueError(f"Fuente alterna no encontrada: {alternate}")

    dato = {
        "etiqueta": etiqueta.strip(),
        "dispositivos": devices,
        "fuente_alterna": alternate,
    }
    _feeders[nombre_elemento.lower()] = dato
    return {"elemento": nombre_elemento, **deepcopy(dato)}


def get_feeder(nombre_elemento: str) -> dict:
    _sync_circuit()
    return deepcopy(
        _feeders.get(
            nombre_elemento.lower(),
            {"etiqueta": "", "dispositivos": [], "fuente_alterna": None},
        )
    )


def snapshot() -> dict:
    _sync_circuit()
    return {
        "circuito": _circuit_name,
        "tipos_carga": deepcopy(_load_types),
        "alimentadores": deepcopy(_feeders),
    }
