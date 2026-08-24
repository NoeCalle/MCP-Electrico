"""Biblioteca técnica trazable de conductores BT/MT.

Reglas de diseño:
- no inventa parámetros faltantes;
- cada conductor conserva fuente y condiciones de ampacidad;
- OpenDSS solo recibe R1/X1 cuando ambos existen para la formación elegida;
- la ampacidad puede aplicarse aun si la impedancia queda pendiente;
- la asignación al alimentador se conserva separada del catálogo de producto.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from opendssdirect import dss

from . import visual_state

_DATA_FILE = Path(__file__).with_name("data") / "conductors_nexans_peru_v1.json"
_catalog_cache: dict[str, Any] | None = None
_assignments: dict[str, dict[str, Any]] = {}
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
        _assignments.clear()
        _circuit_name = current


def reset() -> None:
    global _circuit_name
    _assignments.clear()
    _circuit_name = _active_circuit_name()


def _catalog() -> dict[str, Any]:
    global _catalog_cache
    if _catalog_cache is None:
        _catalog_cache = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    return _catalog_cache


def listar_conductores(
    nivel: str | None = None,
    familia: str | None = None,
) -> list[dict[str, Any]]:
    """Lista conductores disponibles sin ocultar su trazabilidad."""
    level = nivel.strip().upper() if nivel else None
    family = familia.strip().upper() if familia else None
    result = []
    for item in _catalog()["conductors"]:
        if level and str(item.get("level", "")).upper() != level:
            continue
        if family and str(item.get("family", "")).upper() != family:
            continue
        result.append(
            {
                "code": item["code"],
                "level": item["level"],
                "family": item["family"],
                "description": item["description"],
                "section_mm2": item["section_mm2"],
                "screen_section_mm2": item.get("screen_section_mm2"),
                "installations": sorted(item.get("installations", {}).keys()),
                "source": deepcopy(item.get("source", {})),
            }
        )
    return result


def obtener_conductor(codigo: str) -> dict[str, Any]:
    key = codigo.strip().upper()
    for item in _catalog()["conductors"]:
        if str(item["code"]).upper() == key:
            return deepcopy(item)
    raise ValueError(f"Conductor no encontrado en biblioteca: {codigo}")


def obtener_asignacion(nombre_elemento: str) -> dict[str, Any] | None:
    _sync_circuit()
    return deepcopy(_assignments.get(nombre_elemento.lower()))


def snapshot_asignaciones() -> dict[str, Any]:
    _sync_circuit()
    return {
        "circuito": _circuit_name,
        "alimentadores": deepcopy(_assignments),
    }


def _preserve_visual_feeder(nombre_elemento: str, conductor: str, ampacidad_a: float) -> dict:
    current = visual_state.get_feeder(nombre_elemento)
    return visual_state.configure_feeder(
        nombre_elemento,
        etiqueta=current.get("etiqueta", ""),
        dispositivos=current.get("dispositivos", []),
        fuente_alterna=current.get("fuente_alterna"),
        proteccion=current.get("proteccion", "breaker"),
        conductor=conductor,
        corriente_nominal_a=ampacidad_a,
        capacidad_ruptura_ka=current.get("capacidad_ruptura_ka"),
    )


def aplicar_conductor(
    nombre_elemento: str,
    codigo: str,
    instalacion: str,
    actualizar_impedancia: bool = True,
) -> dict[str, Any]:
    """Aplica un producto de catálogo a un objeto ``Line`` de OpenDSS.

    Siempre puede actualizar ``NormAmps`` si la instalación tiene ampacidad
    publicada. Solo modifica R1/X1 cuando el fabricante publica ambos valores
    para la formación asociada a esa instalación.
    """
    _sync_circuit()
    full_name = nombre_elemento.strip()
    if "." not in full_name:
        full_name = f"Line.{full_name}"
    if not full_name.lower().startswith("line."):
        raise ValueError("La biblioteca v1 solo puede aplicarse a elementos Line.*")
    if not dss.Circuit.SetActiveElement(full_name):
        raise ValueError(f"Elemento no encontrado en el circuito: {full_name}")

    product = obtener_conductor(codigo)
    installation_key = instalacion.strip().lower()
    installation = product.get("installations", {}).get(installation_key)
    if not installation:
        options = ", ".join(sorted(product.get("installations", {})))
        raise ValueError(
            f"Instalación no disponible para {product['code']}: {instalacion}. "
            f"Opciones: {options}"
        )

    ampacity = float(installation["ampacity_a"])
    formation = installation.get("formation")
    impedance = (product.get("impedance_by_formation") or {}).get(formation or "", {})
    r1 = impedance.get("rac90_ohm_km")
    x1 = impedance.get("x60_ohm_km")

    impedance_updated = False
    impedance_reason = None
    edit_parts = [f"NormAmps={ampacity}"]
    if actualizar_impedancia and r1 is not None and x1 is not None:
        edit_parts.extend([f"R1={float(r1)}", f"X1={float(x1)}"])
        impedance_updated = True
    elif actualizar_impedancia:
        impedance_reason = (
            "El fabricante no publica Rca90 y X60 completos para la formación "
            "seleccionada; se conserva la impedancia OpenDSS previa."
        )
    else:
        impedance_reason = "Actualización de impedancia desactivada por el usuario."

    dss(f"Edit {full_name} {' '.join(edit_parts)}")

    label = product["description"]
    _preserve_visual_feeder(full_name, label, ampacity)

    assignment = {
        "elemento": full_name,
        "codigo": product["code"],
        "instalacion": installation_key,
        "descripcion": label,
        "ampacidad_aplicada_a": ampacity,
        "formacion": formation,
        "r1_aplicado_ohm_km": float(r1) if impedance_updated else None,
        "x1_aplicado_ohm_km": float(x1) if impedance_updated else None,
        "impedancia_actualizada": impedance_updated,
        "motivo_impedancia_no_actualizada": impedance_reason,
        "fuente": deepcopy(product["source"]),
        "condiciones_ampacidad": deepcopy(installation),
        "producto": {
            "nivel": product["level"],
            "familia": product["family"],
            "fabricante": product["manufacturer"],
            "referencia": product.get("product_ref"),
            "seccion_mm2": product["section_mm2"],
            "pantalla_mm2": product.get("screen_section_mm2"),
            "rdc20_ohm_km": product.get("rdc20_ohm_km"),
        },
    }
    _assignments[full_name.lower()] = assignment
    return deepcopy(assignment)
