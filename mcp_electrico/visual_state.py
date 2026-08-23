"""Metadatos visuales del unifilar que no alteran el cálculo OpenDSS.

La capa visual describe cómo debe interpretarse el modelo en un diagrama:
qué buses son barras físicas, cómo se rotulan cargas y alimentadores, qué
protección se muestra y qué equipos gráficos (ATS/UPS) se intercalan.

Nada de este módulo modifica impedancias, topología o resultados eléctricos.
"""

from __future__ import annotations

from copy import deepcopy

from opendssdirect import dss

VALID_LOAD_TYPES = {"tablero", "motor", "carga"}
VALID_INLINE_DEVICES = {"ats", "ups"}
VALID_BUS_ROLES = {"auto", "barra", "conexion"}
VALID_PROTECTIONS = {"breaker", "mccb", "acb", "fuse", "isolator"}

_load_types: dict[str, str] = {}
_load_labels: dict[str, str] = {}
_feeders: dict[str, dict] = {}
_buses: dict[str, dict] = {}
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
        _load_labels.clear()
        _feeders.clear()
        _buses.clear()
        _circuit_name = current


def reset() -> None:
    global _circuit_name
    _load_types.clear()
    _load_labels.clear()
    _feeders.clear()
    _buses.clear()
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


def set_load_label(nombre_carga: str, etiqueta: str) -> dict:
    """Define un rótulo de ingeniería para una carga sin renombrarla en OpenDSS."""
    _sync_circuit()
    disponibles = {n.lower() for n in dss.Loads.AllNames()}
    if nombre_carga.lower() not in disponibles:
        raise ValueError(f"Carga no encontrada en el circuito: {nombre_carga}")
    _load_labels[nombre_carga.lower()] = etiqueta.strip()
    return {"carga": nombre_carga, "etiqueta": etiqueta.strip()}


def get_load_type(nombre_carga: str) -> str:
    _sync_circuit()
    return _load_types.get(nombre_carga.lower(), "tablero")


def get_load_label(nombre_carga: str) -> str:
    _sync_circuit()
    return _load_labels.get(nombre_carga.lower(), "")


def configure_bus(nombre_bus: str, rol: str = "auto", etiqueta: str = "") -> dict:
    """Fuerza un bus a verse como barra física o como conexión lógica.

    ``rol``:
    - ``auto``: el renderer decide según la función eléctrica del bus;
    - ``barra``: siempre se dibuja como barra;
    - ``conexion``: se evita dibujarlo como barra.
    """
    _sync_circuit()
    role = rol.strip().lower()
    if role not in VALID_BUS_ROLES:
        admitidos = ", ".join(sorted(VALID_BUS_ROLES))
        raise ValueError(f"rol no válido: {rol}. Admitidos: {admitidos}.")
    disponibles = {n.lower() for n in dss.Circuit.AllBusNames()}
    if nombre_bus.lower() not in disponibles:
        raise ValueError(f"Bus no encontrado en el circuito: {nombre_bus}")
    dato = {"rol": role, "etiqueta": etiqueta.strip()}
    _buses[nombre_bus.lower()] = dato
    return {"bus": nombre_bus, **deepcopy(dato)}


def get_bus(nombre_bus: str) -> dict:
    _sync_circuit()
    return deepcopy(
        _buses.get(nombre_bus.lower(), {"rol": "auto", "etiqueta": ""})
    )


def configure_feeder(
    nombre_elemento: str,
    etiqueta: str = "",
    dispositivos: list[str] | None = None,
    fuente_alterna: str | None = None,
    proteccion: str = "breaker",
    conductor: str = "",
    corriente_nominal_a: float | None = None,
    capacidad_ruptura_ka: float | None = None,
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

    protection = proteccion.strip().lower()
    if protection not in VALID_PROTECTIONS:
        admitidos = ", ".join(sorted(VALID_PROTECTIONS))
        raise ValueError(
            f"proteccion no válida: {proteccion}. Admitidas: {admitidos}."
        )

    if corriente_nominal_a is not None and corriente_nominal_a <= 0:
        raise ValueError("corriente_nominal_a debe ser positiva.")
    if capacidad_ruptura_ka is not None and capacidad_ruptura_ka <= 0:
        raise ValueError("capacidad_ruptura_ka debe ser positiva.")

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
        "proteccion": protection,
        "conductor": conductor.strip(),
        "corriente_nominal_a": float(corriente_nominal_a)
        if corriente_nominal_a is not None
        else None,
        "capacidad_ruptura_ka": float(capacidad_ruptura_ka)
        if capacidad_ruptura_ka is not None
        else None,
    }
    _feeders[nombre_elemento.lower()] = dato
    return {"elemento": nombre_elemento, **deepcopy(dato)}


def get_feeder(nombre_elemento: str) -> dict:
    _sync_circuit()
    return deepcopy(
        _feeders.get(
            nombre_elemento.lower(),
            {
                "etiqueta": "",
                "dispositivos": [],
                "fuente_alterna": None,
                "proteccion": "breaker",
                "conductor": "",
                "corriente_nominal_a": None,
                "capacidad_ruptura_ka": None,
            },
        )
    )


def snapshot() -> dict:
    _sync_circuit()
    return {
        "circuito": _circuit_name,
        "tipos_carga": deepcopy(_load_types),
        "etiquetas_carga": deepcopy(_load_labels),
        "alimentadores": deepcopy(_feeders),
        "buses": deepcopy(_buses),
    }
