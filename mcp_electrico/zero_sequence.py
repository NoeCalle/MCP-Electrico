"""Datos profesionales P2 de secuencia cero.

Este módulo mantiene separados los datos homopolares del modelo positivo-
secuencia. No deriva Z0 desde Z1, Scc3, R1/X1 ni desde valores por defecto de
los motores.

Proyección actual:
- Vsource: R0/X0 explícitos pueden aplicarse directamente a OpenDSS.
- Line: R0/X0/C0 explícitos pueden aplicarse directamente a OpenDSS.
- Transformer: se almacena una ficha canónica de secuencia cero compatible
  con la futura proyección IEC 60909/pandapower, pero NO se fuerza una
  proyección OpenDSS porque la respuesta homopolar depende de conexión,
  puesta a tierra y estructura magnética del transformador.
"""

from __future__ import annotations

from copy import deepcopy
from math import sqrt
from typing import Any

from opendssdirect import dss

from . import professional_data

_circuit_name = ""
_source: dict[str, Any] | None = None
_lines: dict[str, dict[str, Any]] = {}
_transformers: dict[str, dict[str, Any]] = {}


def _active_circuit_name() -> str:
    try:
        return str(dss.Circuit.Name() or "")
    except Exception:
        return ""


def _sync() -> None:
    global _circuit_name, _source
    current = _active_circuit_name()
    if current == _circuit_name:
        return
    _circuit_name = current
    _source = None
    _lines.clear()
    _transformers.clear()


def reset() -> None:
    global _circuit_name, _source
    _circuit_name = _active_circuit_name()
    _source = None
    _lines.clear()
    _transformers.clear()


def _provenance(reference: str | None, url: str | None) -> dict[str, Any]:
    return {
        "origin": "usuario",
        "reference": reference or "dato_explicito_usuario",
        "url": url,
    }


def _validate_rx(code: str, r: float, x: float, label: str) -> tuple[float, float]:
    rr, xx = float(r), float(x)
    if rr < 0 or xx < 0 or (rr == 0 and xx == 0):
        raise ValueError(f"{code}: {label} requiere R>=0, X>=0 y Z distinta de cero.")
    return rr, xx


def _source_pair(name: str, r0: float | None, x0: float | None) -> dict[str, float] | None:
    if r0 is None and x0 is None:
        return None
    if r0 is None or x0 is None:
        raise ValueError(f"P2Z003: escenario {name} requiere r0_ohm y x0_ohm juntos.")
    rr, xx = _validate_rx("P2Z004", r0, x0, f"Z0 del escenario {name}")
    return {"r0_ohm": rr, "x0_ohm": xx, "z0_ohm": sqrt(rr * rr + xx * xx)}


def _apply_active_source() -> dict[str, Any]:
    global _source
    if _source is None:
        return {"applied": False, "reason": "secuencia cero de fuente no definida"}
    p2 = professional_data.obtener_red_equivalente()
    if not p2:
        return {"applied": False, "reason": "red equivalente P2 no definida"}
    active = str(p2.get("active_scenario") or "max")
    values = _source["scenarios"].get(active)
    if values is None:
        projection = {
            "applied": False,
            "scenario": active,
            "reason": f"Z0 explícita no definida para escenario {active}",
        }
        _source["active_projection"] = projection
        return deepcopy(projection)
    dss(
        f"Edit Vsource.source R0={values['r0_ohm']} X0={values['x0_ohm']}"
    )
    projection = {
        "applied": True,
        "scenario": active,
        "r0_ohm": values["r0_ohm"],
        "x0_ohm": values["x0_ohm"],
        "engine": "OpenDSS",
        "method": "Vsource.R0/X0 explícitos",
    }
    _source["active_projection"] = projection
    return deepcopy(projection)


def definir_fuente(
    r0_max_ohm: float,
    x0_max_ohm: float,
    r0_min_ohm: float | None = None,
    x0_min_ohm: float | None = None,
    fuente_referencia: str | None = None,
    fuente_url: str | None = None,
) -> dict[str, Any]:
    """Define Z0 explícita de la red aguas arriba por escenario.

    No calcula Z0 desde Scc3. Si existe escenario mínimo positivo-secuencia,
    su Z0 puede omitirse, pero ese escenario quedará no apto para falla a
    tierra hasta que se suministre explícitamente.
    """
    _sync()
    global _source
    p2 = professional_data.obtener_red_equivalente()
    if not p2:
        raise ValueError("P2Z001: primero debe definirse la red equivalente P2.")
    max_values = _source_pair("max", r0_max_ohm, x0_max_ohm)
    min_values = _source_pair("min", r0_min_ohm, x0_min_ohm)
    if min_values is not None and p2.get("scenarios", {}).get("min") is None:
        raise ValueError("P2Z002: se recibió Z0 mínima pero no existe escenario mínimo P2.")
    _source = {
        "available": True,
        "status": "EXPLICIT",
        "scenarios": {"max": max_values, "min": min_values},
        "provenance": _provenance(fuente_referencia, fuente_url),
        "note": "R0/X0 suministrados explícitamente; no derivados desde Scc3 ni Z1.",
    }
    _apply_active_source()
    return deepcopy(_source)


def reapply_active_source() -> dict[str, Any]:
    """Reaplica Z0 al cambiar max/min sin sustituir datos faltantes."""
    _sync()
    return _apply_active_source()


def definir_linea(
    nombre_elemento: str,
    r0_ohm_km: float,
    x0_ohm_km: float,
    c0_nf_km: float | None = None,
    fuente_referencia: str | None = None,
    fuente_url: str | None = None,
) -> dict[str, Any]:
    """Define R0/X0 y opcional C0 explícitos para una Line trifásica."""
    _sync()
    full = str(nombre_elemento).strip()
    if "." not in full:
        full = f"Line.{full}"
    if not full.lower().startswith("line."):
        raise ValueError("P2ZL001: el elemento debe ser Line.*")
    if not dss.Circuit.SetActiveElement(full):
        raise ValueError(f"P2ZL002: elemento no encontrado: {full}")
    if int(dss.CktElement.NumPhases()) != 3:
        raise ValueError("P2ZL003: la representación R0/X0 v1 se limita a líneas trifásicas.")
    rr, xx = _validate_rx("P2ZL004", r0_ohm_km, x0_ohm_km, "Z0 de línea")
    if c0_nf_km is not None and float(c0_nf_km) < 0:
        raise ValueError("P2ZL005: c0_nf_km no puede ser negativa.")
    edit = [f"R0={rr}", f"X0={xx}"]
    if c0_nf_km is not None:
        edit.append(f"C0={float(c0_nf_km)}")
    dss(f"Edit {full} {' '.join(edit)}")
    record = {
        "element": full,
        "available": True,
        "status": "EXPLICIT",
        "r0_ohm_km": rr,
        "x0_ohm_km": xx,
        "z0_ohm_km": sqrt(rr * rr + xx * xx),
        "c0_nf_km": float(c0_nf_km) if c0_nf_km is not None else None,
        "provenance": _provenance(fuente_referencia, fuente_url),
        "projection": {
            "opendss_ready": True,
            "applied": True,
            "method": "Line.R0/X0/C0 explícitos en definición de componentes simétricas",
        },
    }
    _lines[full.lower()] = record
    return deepcopy(record)


def definir_transformador(
    nombre_elemento: str,
    uk0_percent: float,
    ur0_percent: float,
    magnetizing_z0_ratio_percent: float,
    magnetizing_r_over_x: float,
    leakage_share_hv: float,
    neutral_side: str | None = None,
    neutral_mode: str | None = None,
    rn_ohm: float | None = None,
    xn_ohm: float | None = None,
    fuente_referencia: str | None = None,
    fuente_url: str | None = None,
) -> dict[str, Any]:
    """Registra la ficha homopolar del transformador sin forzar OpenDSS.

    Los parámetros son canónicos y su proyección pandapower queda declarada.
    No se iguala Z0 a Z1 y no se estima el efecto del núcleo.
    """
    _sync()
    full = str(nombre_elemento).strip()
    if "." not in full:
        full = f"Transformer.{full}"
    if not full.lower().startswith("transformer."):
        raise ValueError("P2ZT001: el elemento debe ser Transformer.*")
    p2 = professional_data.obtener_transformador(full)
    if not p2:
        raise ValueError(f"P2ZT002: no existe ficha profesional P2 para {full}.")

    uk0 = float(uk0_percent)
    ur0 = float(ur0_percent)
    mag_ratio = float(magnetizing_z0_ratio_percent)
    mag_rx = float(magnetizing_r_over_x)
    share = float(leakage_share_hv)
    if uk0 <= 0 or ur0 < 0 or ur0 > uk0:
        raise ValueError("P2ZT003: se requiere uk0>0 y 0<=ur0<=uk0.")
    if mag_ratio < 0 or mag_rx < 0:
        raise ValueError("P2ZT004: parámetros magnetizantes de secuencia cero no pueden ser negativos.")
    if not 0 <= share <= 1:
        raise ValueError("P2ZT005: leakage_share_hv debe estar entre 0 y 1.")

    mode = str(neutral_mode).lower() if neutral_mode is not None else None
    side = str(neutral_side).lower() if neutral_side is not None else None
    if (mode is None) != (side is None):
        raise ValueError("P2ZT006: neutral_side y neutral_mode deben declararse juntos.")
    if side is not None and side not in {"hv", "lv"}:
        raise ValueError("P2ZT007: neutral_side debe ser 'hv' o 'lv'.")
    if mode is not None and mode not in {"solid", "impedance", "ungrounded"}:
        raise ValueError("P2ZT008: neutral_mode debe ser solid, impedance o ungrounded.")
    if side is not None:
        connection = p2.get("vector_group", {}).get(f"{side}_connection")
        if connection != "wye":
            raise ValueError(f"P2ZT009: el lado {side} no es wye; no puede declararse neutro allí.")

    rn = float(rn_ohm) if rn_ohm is not None else None
    xn = float(xn_ohm) if xn_ohm is not None else None
    if mode == "solid":
        if rn not in {None, 0.0} or xn not in {None, 0.0}:
            raise ValueError("P2ZT010: neutro solid no admite impedancia distinta de cero.")
        rn, xn = 0.0, 0.0
    elif mode == "impedance":
        if rn is None or xn is None:
            raise ValueError("P2ZT011: neutro impedance requiere rn_ohm y xn_ohm explícitos.")
        _validate_rx("P2ZT012", rn, xn, "impedancia de neutro")
    elif mode == "ungrounded":
        if rn is not None or xn is not None:
            raise ValueError("P2ZT013: neutro ungrounded no admite rn/xn finitos.")

    x0_percent = sqrt(max(uk0 * uk0 - ur0 * ur0, 0.0))
    record = {
        "element": full,
        "available": True,
        "status": "EXPLICIT",
        "impedance": {
            "uk0_percent": uk0,
            "ur0_percent": ur0,
            "ux0_percent": x0_percent,
            "magnetizing_z0_ratio_percent": mag_ratio,
            "magnetizing_r_over_x": mag_rx,
            "leakage_share_hv": share,
        },
        "neutral": {
            "side": side,
            "mode": mode,
            "rn_ohm": rn,
            "xn_ohm": xn,
            "ground_path_declared": mode in {"solid", "impedance"},
        },
        "provenance": _provenance(fuente_referencia, fuente_url),
        "projection": {
            "pandapower_ready": True,
            "pandapower": {
                "vk0_percent": uk0,
                "vkr0_percent": ur0,
                "mag0_percent": mag_ratio,
                "mag0_rx": mag_rx,
                "si0_hv_partial": share,
                "rn_ohm": rn if mode in {"solid", "impedance"} else None,
                "xn_ohm": xn if mode in {"solid", "impedance"} else None,
            },
            "opendss_ready": False,
            "opendss_reason": (
                "La ficha Z0 no se proyecta automáticamente al Transformer de OpenDSS: "
                "la respuesta homopolar depende de conexión, neutro y estructura magnética. "
                "Se requiere una estrategia de modelado específica y validada."
            ),
        },
    }
    _transformers[full.lower()] = record
    return deepcopy(record)


def obtener_fuente() -> dict[str, Any] | None:
    _sync()
    return deepcopy(_source)


def obtener_linea(nombre_elemento: str) -> dict[str, Any] | None:
    _sync()
    full = str(nombre_elemento)
    if "." not in full:
        full = f"Line.{full}"
    return deepcopy(_lines.get(full.lower()))


def obtener_transformador(nombre_elemento: str) -> dict[str, Any] | None:
    _sync()
    full = str(nombre_elemento)
    if "." not in full:
        full = f"Transformer.{full}"
    return deepcopy(_transformers.get(full.lower()))


def snapshot() -> dict[str, Any]:
    _sync()
    return {
        "schema_version": 1,
        "circuit": _circuit_name,
        "source": deepcopy(_source),
        "lines": [deepcopy(v) for _, v in sorted(_lines.items())],
        "transformers": [deepcopy(v) for _, v in sorted(_transformers.items())],
    }
