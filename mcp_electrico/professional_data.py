"""Datos profesionales P2 y proyección trazable hacia OpenDSS.

Este módulo almacena únicamente datos explícitos o derivados mediante fórmulas
registradas. No completa parámetros faltantes con valores típicos.

Alcance P2 v1:
- transformadores trifásicos de dos devanados;
- grupos vectoriales comunes representables directamente por OpenDSS;
- impedancia de cortocircuito a partir de ``uk_percent`` + ``x_r`` o pérdidas
  de carga explícitas;
- taps discretos por relación;
- pérdidas en vacío / corriente de vacío cuando se suministran;
- red equivalente positiva-secuencia con Scc3 y X/R para escenarios máximo y
  mínimo.

La secuencia cero NO se deriva de Scc3. Mientras no se suministre una extensión
posterior, queda marcada como no disponible para estudios que la requieran.
"""

from __future__ import annotations

from copy import deepcopy
from math import sqrt
import re
from typing import Any

from opendssdirect import dss


_circuit_name = ""
_transformers: dict[str, dict[str, Any]] = {}
_source: dict[str, Any] | None = None


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
    _transformers.clear()
    _source = None


def reset() -> None:
    """Limpia metadatos P2 sin modificar OpenDSS."""
    global _circuit_name, _source
    _circuit_name = _active_circuit_name()
    _transformers.clear()
    _source = None


def _provenance(reference: str | None, url: str | None, fields: list[str]) -> dict[str, Any]:
    base = {
        "origin": "usuario",
        "reference": reference or "dato_explicito_usuario",
        "url": url,
    }
    return {field: deepcopy(base) for field in fields}


def _parse_vector_group(group: str) -> dict[str, Any]:
    text = str(group or "").strip()
    match = re.fullmatch(r"([DY])([dy])n?(0|1|11)", text, re.IGNORECASE)
    if not match:
        raise ValueError(
            "P2TR003: grupo_vectorial v1 admite únicamente Dd0, Yy0, Dyn1, Dyn11, Yd1 o Yd11. "
            "No se aproxima un grupo no representable directamente."
        )
    hv_code, lv_code, clock_raw = match.groups()
    hv_code = hv_code.upper()
    lv_code = lv_code.lower()
    clock = int(clock_raw)
    hv_conn = "delta" if hv_code == "D" else "wye"
    lv_conn = "delta" if lv_code == "d" else "wye"
    mixed = hv_conn != lv_conn
    if not mixed and clock != 0:
        raise ValueError("P2TR004: conexiones iguales solo se admiten con reloj 0 en P2 v1.")
    if mixed and clock not in (1, 11):
        raise ValueError("P2TR005: conexión delta-wye/wye-delta requiere reloj 1 u 11 en P2 v1.")
    lead_lag = None
    if mixed:
        lead_lag = "Lag" if clock == 1 else "Lead"
    # Convención de reloj: 1 -> LV atrasada 30°, 11 -> LV adelantada 30°.
    shift_degree = -30.0 if clock == 1 else (30.0 if clock == 11 else 0.0)
    vector_pp = f"{hv_code}{lv_code}"
    if "n" in text.lower() and lv_code == "y":
        vector_pp += "n"
    return {
        "grupo_vectorial": text,
        "hv_connection": hv_conn,
        "lv_connection": lv_conn,
        "clock": clock,
        "lead_lag_opendss": lead_lag,
        "shift_degree": shift_degree,
        "vector_group_pandapower": vector_pp,
    }


def _series_impedance(
    kva: float,
    uk_percent: float,
    x_r: float | None,
    load_loss_kw: float | None,
) -> dict[str, float]:
    if kva <= 0 or uk_percent <= 0:
        raise ValueError("P2TR010: kva y uk_percent deben ser mayores que cero.")
    if load_loss_kw is not None:
        if load_loss_kw < 0:
            raise ValueError("P2TR011: load_loss_kw no puede ser negativo.")
        r_percent = float(load_loss_kw) / float(kva) * 100.0
        if r_percent >= uk_percent:
            raise ValueError("P2TR012: las pérdidas de carga implican R% >= uk%; revise los datos.")
        x_percent = sqrt(uk_percent**2 - r_percent**2)
        xr_effective = x_percent / r_percent if r_percent > 0 else float("inf")
        if x_r is not None and x_r > 0 and r_percent > 0:
            mismatch = abs(xr_effective - x_r) / x_r
            if mismatch > 0.10:
                raise ValueError(
                    "P2TR013: x_r y load_loss_kw son incompatibles (>10% de diferencia). "
                    "No se elige silenciosamente uno de los dos."
                )
        method = "uk_percent + load_loss_kw"
    else:
        if x_r is None or x_r <= 0:
            raise ValueError("P2TR014: se requiere x_r>0 o load_loss_kw para separar R y X.")
        r_percent = uk_percent / sqrt(1.0 + x_r**2)
        x_percent = r_percent * x_r
        xr_effective = float(x_r)
        method = "uk_percent + x_r"
    return {
        "r_percent_total": r_percent,
        "x_percent": x_percent,
        "x_r_effective": xr_effective,
        "method": method,
    }


def _tap_data(
    tap_side: str | None,
    tap_neutral: int,
    tap_min: int,
    tap_max: int,
    tap_step_percent: float | None,
    tap_pos: int,
) -> dict[str, Any]:
    if tap_side is None or tap_step_percent is None:
        return {
            "enabled": False,
            "side": None,
            "neutral": 0,
            "min": 0,
            "max": 0,
            "step_percent": None,
            "position": 0,
            "tap_pu": 1.0,
        }
    side = str(tap_side).lower()
    if side not in {"hv", "lv"}:
        raise ValueError("P2TR020: tap_side debe ser 'hv', 'lv' o None.")
    if tap_step_percent <= 0:
        raise ValueError("P2TR021: tap_step_percent debe ser positivo.")
    if not (tap_min <= tap_neutral <= tap_max and tap_min <= tap_pos <= tap_max):
        raise ValueError("P2TR022: posiciones de tap fuera del rango declarado.")
    tap_pu = 1.0 + (tap_pos - tap_neutral) * tap_step_percent / 100.0
    return {
        "enabled": True,
        "side": side,
        "neutral": int(tap_neutral),
        "min": int(tap_min),
        "max": int(tap_max),
        "step_percent": float(tap_step_percent),
        "position": int(tap_pos),
        "tap_pu": tap_pu,
    }


def agregar_transformador_profesional(
    nombre: str,
    bus_hv: str,
    bus_lv: str,
    kva: float,
    kv_hv: float,
    kv_lv: float,
    uk_percent: float,
    grupo_vectorial: str,
    x_r: float | None = None,
    load_loss_kw: float | None = None,
    no_load_loss_kw: float | None = None,
    i0_percent: float | None = None,
    tap_side: str | None = None,
    tap_neutral: int = 0,
    tap_min: int = 0,
    tap_max: int = 0,
    tap_step_percent: float | None = None,
    tap_pos: int = 0,
    fabricante: str | None = None,
    modelo: str | None = None,
    fuente_referencia: str | None = None,
    fuente_url: str | None = None,
) -> dict[str, Any]:
    """Crea y registra un transformador profesional de dos devanados.

    ``uk_percent`` es la magnitud de la tensión de cortocircuito. Para separar
    R/X se exige ``x_r`` o ``load_loss_kw``. Si ambos existen y son
    incompatibles, la operación falla.
    """
    _sync()
    if not _circuit_name:
        raise ValueError("P2TR001: no existe un circuito activo.")
    if min(float(kva), float(kv_hv), float(kv_lv), float(uk_percent)) <= 0:
        raise ValueError("P2TR002: kva, tensiones y uk_percent deben ser positivos.")
    existing = {str(x).lower() for x in dss.Transformers.AllNames()}
    if nombre.lower() in existing:
        raise ValueError(f"P2TR006: Transformer.{nombre} ya existe.")
    if no_load_loss_kw is not None and no_load_loss_kw < 0:
        raise ValueError("P2TR015: no_load_loss_kw no puede ser negativo.")
    if i0_percent is not None and i0_percent < 0:
        raise ValueError("P2TR016: i0_percent no puede ser negativo.")

    vg = _parse_vector_group(grupo_vectorial)
    series = _series_impedance(float(kva), float(uk_percent), x_r, load_loss_kw)
    tap = _tap_data(tap_side, tap_neutral, tap_min, tap_max, tap_step_percent, tap_pos)

    r_half = series["r_percent_total"] / 2.0
    noload_pct = (float(no_load_loss_kw) / float(kva) * 100.0) if no_load_loss_kw is not None else 0.0
    imag_pct = float(i0_percent) if i0_percent is not None else 0.0
    hv_tap = tap["tap_pu"] if tap["enabled"] and tap["side"] == "hv" else 1.0
    lv_tap = tap["tap_pu"] if tap["enabled"] and tap["side"] == "lv" else 1.0

    command = (
        f"New Transformer.{nombre} Phases=3 Windings=2 "
        f"Buses=[{bus_hv},{bus_lv}] "
        f"Conns=[{vg['hv_connection']},{vg['lv_connection']}] "
        f"kVs=[{float(kv_hv)},{float(kv_lv)}] kVAs=[{float(kva)},{float(kva)}] "
        f"%Rs=[{r_half},{r_half}] XHL={series['x_percent']} "
        f"%Noloadloss={noload_pct} %imag={imag_pct} Taps=[{hv_tap},{lv_tap}]"
    )
    if vg["lead_lag_opendss"]:
        command += f" LeadLag={vg['lead_lag_opendss']}"
    dss(command)

    if tap["enabled"]:
        wdg = 1 if tap["side"] == "hv" else 2
        min_pu = 1.0 + (tap["min"] - tap["neutral"]) * tap["step_percent"] / 100.0
        max_pu = 1.0 + (tap["max"] - tap["neutral"]) * tap["step_percent"] / 100.0
        num_taps = int(tap["max"] - tap["min"])
        dss(
            f"Edit Transformer.{nombre} Wdg={wdg} MinTap={min_pu} MaxTap={max_pu} NumTaps={num_taps} Tap={tap['tap_pu']}"
        )

    fields = [
        "kva", "kv_hv", "kv_lv", "uk_percent", "grupo_vectorial",
        "x_r", "load_loss_kw", "no_load_loss_kw", "i0_percent", "taps",
    ]
    record = {
        "id": f"Transformer.{nombre}",
        "name": nombre,
        "buses": {"hv": bus_hv.split(".")[0], "lv": bus_lv.split(".")[0]},
        "rating": {"kva": float(kva), "kv_hv": float(kv_hv), "kv_lv": float(kv_lv)},
        "vector_group": vg,
        "short_circuit": {
            "uk_percent": float(uk_percent),
            "x_r_input": float(x_r) if x_r is not None else None,
            "load_loss_kw": float(load_loss_kw) if load_loss_kw is not None else None,
            **series,
        },
        "losses": {
            "no_load_loss_kw": float(no_load_loss_kw) if no_load_loss_kw is not None else None,
            "i0_percent": float(i0_percent) if i0_percent is not None else None,
        },
        "tap": tap,
        "manufacturer": fabricante,
        "model": modelo,
        "provenance": _provenance(fuente_referencia, fuente_url, fields),
        "projection": {
            "opendss": {
                "r_percent_each_winding": r_half,
                "xhl_percent": series["x_percent"],
                "noloadloss_percent": noload_pct,
                "imag_percent": imag_pct,
                "lead_lag": vg["lead_lag_opendss"],
            },
            "pandapower_ready": True,
            "zero_sequence_ready": False,
        },
    }
    _transformers[record["id"].lower()] = record
    return deepcopy(record)


def _source_scenario(name: str, scc_mva: float | None, x_r: float | None) -> dict[str, Any] | None:
    if scc_mva is None and x_r is None:
        return None
    if scc_mva is None or x_r is None or scc_mva <= 0 or x_r <= 0:
        raise ValueError(f"P2SRC010: escenario {name} requiere scc_mva>0 y x_r>0 juntos.")
    return {"scc3_mva": float(scc_mva), "x_r": float(x_r)}


def _apply_source_scenario(record: dict[str, Any]) -> dict[str, Any]:
    scenario_name = record["active_scenario"]
    scenario = record["scenarios"].get(scenario_name)
    if scenario is None:
        raise ValueError(f"P2SRC020: escenario {scenario_name} no está definido.")
    dss(
        f"Edit Vsource.source BasekV={record['kv_ll']} MVAsc3={scenario['scc3_mva']} X1R1={scenario['x_r']}"
    )
    z1 = record["kv_ll"] ** 2 / scenario["scc3_mva"]
    r1 = z1 / sqrt(1.0 + scenario["x_r"] ** 2)
    x1 = r1 * scenario["x_r"]
    return {"z1_ohm": z1, "r1_ohm": r1, "x1_ohm": x1}


def definir_red_equivalente(
    kv_ll: float,
    scc_max_mva: float,
    x_r_max: float,
    scc_min_mva: float | None = None,
    x_r_min: float | None = None,
    escenario_activo: str = "max",
    fuente_referencia: str | None = None,
    fuente_url: str | None = None,
) -> dict[str, Any]:
    """Define el equivalente positivo-secuencia de la red aguas arriba.

    No deriva MVAsc1, R0 ni X0. Por ello el registro no es suficiente para una
    falla monofásica normativa y lo declara de forma explícita.
    """
    _sync()
    global _source
    if not _circuit_name:
        raise ValueError("P2SRC001: no existe un circuito activo.")
    if kv_ll <= 0:
        raise ValueError("P2SRC002: kv_ll debe ser positivo.")
    max_s = _source_scenario("max", scc_max_mva, x_r_max)
    min_s = _source_scenario("min", scc_min_mva, x_r_min)
    active = str(escenario_activo).lower()
    if active not in {"max", "min"}:
        raise ValueError("P2SRC003: escenario_activo debe ser 'max' o 'min'.")
    if active == "min" and min_s is None:
        raise ValueError("P2SRC004: no puede activarse el escenario mínimo si no fue definido.")
    provenance = _provenance(
        fuente_referencia,
        fuente_url,
        ["kv_ll", "scc_max_mva", "x_r_max", "scc_min_mva", "x_r_min"],
    )
    record = {
        "id": "Source.sourcebus",
        "mode": "thevenin_positive_sequence",
        "kv_ll": float(kv_ll),
        "scenarios": {"max": max_s, "min": min_s},
        "active_scenario": active,
        "provenance": provenance,
        "zero_sequence": {
            "available": False,
            "status": "NOT_AVAILABLE",
            "note": "Scc3 y X/R no determinan por sí solos Z0; no se inventa MVAsc1/R0/X0.",
        },
    }
    record["active_equivalent"] = _apply_source_scenario(record)
    _source = record
    return deepcopy(record)


def seleccionar_escenario_red(escenario: str) -> dict[str, Any]:
    _sync()
    global _source
    if _source is None:
        raise ValueError("P2SRC021: no existe una red equivalente P2 definida.")
    name = str(escenario).lower()
    if name not in {"max", "min"} or _source["scenarios"].get(name) is None:
        raise ValueError(f"P2SRC022: escenario {name!r} no disponible.")
    _source["active_scenario"] = name
    _source["active_equivalent"] = _apply_source_scenario(_source)
    return deepcopy(_source)


def obtener_transformador(nombre_o_id: str) -> dict[str, Any] | None:
    _sync()
    key = str(nombre_o_id)
    if not key.lower().startswith("transformer."):
        key = f"Transformer.{key}"
    item = _transformers.get(key.lower())
    return deepcopy(item) if item else None


def obtener_red_equivalente() -> dict[str, Any] | None:
    _sync()
    return deepcopy(_source)


def snapshot() -> dict[str, Any]:
    _sync()
    return {
        "schema_version": 1,
        "circuit": _circuit_name,
        "source": deepcopy(_source),
        "transformers": [deepcopy(v) for _, v in sorted(_transformers.items())],
    }
