"""Estudios operativos derivados de la solución OpenDSS activa.

Este módulo ejecuta y organiza métricas de ingeniería sin sustituir a OpenDSS
como motor eléctrico. Las clasificaciones (por ejemplo, un límite de caída de
tensión) son criterios configurables del usuario y se conservan separadas del
resultado eléctrico calculado.
"""

from __future__ import annotations

from typing import Any

from opendssdirect import dss

from . import core, visual_state


def _bus_name(raw: str) -> str:
    return str(raw).split(".")[0]


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _bus_voltage_summary(powerflow: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bus, info in powerflow.get("voltajes_por_bus", {}).items():
        volts = [float(v) for v in info.get("voltajes_pu", [])]
        avg = _mean(volts)
        rows.append(
            {
                "id": f"Bus.{bus}",
                "bus": bus,
                "kv_base_ln": info.get("kv_base"),
                "voltajes_pu": volts,
                "vpu_min": round(min(volts), 4) if volts else None,
                "vpu_promedio": round(avg, 4) if avg is not None else None,
                "vpu_max": round(max(volts), 4) if volts else None,
                "desviacion_desde_1pu_pct": (
                    round((1.0 - avg) * 100.0, 3) if avg is not None else None
                ),
            }
        )
    return rows


def _active_line_measurements(name: str) -> dict[str, Any]:
    """Extrae magnitudes del terminal 1 de una línea ya resuelta.

    `CurrentsMagAng` y `Powers` se interpretan por conductor y terminal. Para
    un alimentador convencional se reporta la mayor corriente del terminal 1
    y la suma P/Q de sus conductores. No se usa este dato como ampacidad salvo
    que exista una corriente nominal explícita en los metadatos del usuario.
    """
    full = f"Line.{name}"
    if not dss.Circuit.SetActiveElement(full):
        raise ValueError(f"No se pudo activar {full}.")

    ncond = int(dss.CktElement.NumConductors())
    currents = [float(v) for v in dss.CktElement.CurrentsMagAng()]
    current_mags = currents[0 : 2 * ncond : 2] if ncond > 0 else []

    powers = [float(v) for v in dss.CktElement.Powers()]
    p_terminal = powers[0 : 2 * ncond : 2] if ncond > 0 else []
    q_terminal = powers[1 : 2 * ncond : 2] if ncond > 0 else []

    return {
        "corrientes_terminal1_a": [round(v, 3) for v in current_mags],
        "corriente_max_a": round(max(current_mags), 3) if current_mags else None,
        "flujo_kw_terminal1": round(sum(p_terminal), 3) if p_terminal else None,
        "flujo_kvar_terminal1": round(sum(q_terminal), 3) if q_terminal else None,
    }


def analizar_flujo_operacion() -> dict[str, Any]:
    """Resuelve OpenDSS y agrega métricas por alimentador.

    La cargabilidad solo se calcula si el alimentador tiene
    `corriente_nominal_a` definida como metadato explícito. Ese valor todavía
    no representa una ampacidad normativa derivada por el MCP.
    """
    powerflow = core.ejecutar_flujo_potencia()
    lines: list[dict[str, Any]] = []

    for name in dss.Lines.AllNames():
        dss.Lines.Name(name)
        full = f"Line.{name}"
        visual = visual_state.get_feeder(full)
        measurements = _active_line_measurements(name)
        rating = visual.get("corriente_nominal_a")
        current = measurements.get("corriente_max_a")
        loading = None
        if rating is not None and float(rating) > 0 and current is not None:
            loading = round(float(current) / float(rating) * 100.0, 2)

        lines.append(
            {
                "id": full,
                "name": name,
                "label": visual.get("etiqueta") or name,
                "bus1": _bus_name(dss.Lines.Bus1()),
                "bus2": _bus_name(dss.Lines.Bus2()),
                "longitud_km": round(float(dss.Lines.Length()), 6),
                **measurements,
                "corriente_nominal_a": float(rating) if rating is not None else None,
                "cargabilidad_pct": loading,
                "fuente_corriente_nominal": (
                    "metadato_explicito_usuario" if rating is not None else None
                ),
            }
        )

    max_loading = max(
        (float(x["cargabilidad_pct"]) for x in lines if x["cargabilidad_pct"] is not None),
        default=None,
    )
    max_current = max(
        (float(x["corriente_max_a"]) for x in lines if x["corriente_max_a"] is not None),
        default=None,
    )

    return {
        "convergio": bool(powerflow.get("convergio")),
        "powerflow": powerflow,
        "buses": _bus_voltage_summary(powerflow),
        "alimentadores": lines,
        "resumen": {
            "perdidas_totales_kw": powerflow.get("perdidas_totales_kw"),
            "perdidas_totales_kvar": powerflow.get("perdidas_totales_kvar"),
            "corriente_max_alimentador_a": round(max_current, 3) if max_current is not None else None,
            "cargabilidad_max_pct": round(max_loading, 2) if max_loading is not None else None,
        },
        "nota_cargabilidad": (
            "La cargabilidad solo se reporta cuando existe corriente_nominal_a explícita; "
            "no equivale por sí sola a una verificación normativa de ampacidad."
        ),
    }


def analizar_caida_tension(limite_pct: float = 3.0) -> dict[str, Any]:
    """Calcula caída de tensión por línea usando tensiones pu de buses.

    `limite_pct` es un criterio configurable de evaluación. El MCP no afirma
    que 3 % u otro valor sea universalmente normativo. Se conserva la caída
    firmada promedio y la mayor caída positiva de fase disponible.
    """
    if limite_pct <= 0:
        raise ValueError("limite_pct debe ser mayor que cero.")

    flow = analizar_flujo_operacion()
    pf = flow["powerflow"]
    bus_map = {str(k).lower(): v for k, v in pf.get("voltajes_por_bus", {}).items()}
    rows: list[dict[str, Any]] = []

    for name in dss.Lines.AllNames():
        dss.Lines.Name(name)
        full = f"Line.{name}"
        bus1 = _bus_name(dss.Lines.Bus1())
        bus2 = _bus_name(dss.Lines.Bus2())
        v1 = [float(v) for v in bus_map.get(bus1.lower(), {}).get("voltajes_pu", [])]
        v2 = [float(v) for v in bus_map.get(bus2.lower(), {}).get("voltajes_pu", [])]
        common = min(len(v1), len(v2))
        phase_drop: list[float] = []
        for i in range(common):
            if v1[i] > 0:
                phase_drop.append((v1[i] - v2[i]) / v1[i] * 100.0)

        avg1 = _mean(v1)
        avg2 = _mean(v2)
        signed_avg = (
            (avg1 - avg2) / avg1 * 100.0
            if avg1 is not None and avg2 is not None and avg1 > 0
            else None
        )
        max_positive = max([0.0, *phase_drop]) if phase_drop else None
        evaluated = max_positive if max_positive is not None else max(0.0, signed_avg or 0.0)
        exceeds = evaluated > float(limite_pct)
        visual = visual_state.get_feeder(full)

        rows.append(
            {
                "id": full,
                "name": name,
                "label": visual.get("etiqueta") or name,
                "bus_origen": bus1,
                "bus_destino": bus2,
                "vpu_origen_promedio": round(avg1, 4) if avg1 is not None else None,
                "vpu_destino_promedio": round(avg2, 4) if avg2 is not None else None,
                "caida_pct_fases": [round(v, 3) for v in phase_drop],
                "caida_promedio_pct_firmada": round(signed_avg, 3) if signed_avg is not None else None,
                "caida_evaluada_pct": round(evaluated, 3),
                "limite_pct": float(limite_pct),
                "estado_criterio": "EXCEDE" if exceeds else "OK",
            }
        )

    exceeded = [x for x in rows if x["estado_criterio"] == "EXCEDE"]
    worst = max(rows, key=lambda x: float(x["caida_evaluada_pct"]), default=None)
    buses = _bus_voltage_summary(pf)
    vmins = [x["vpu_min"] for x in buses if x["vpu_min"] is not None]

    return {
        "convergio": bool(flow.get("convergio")),
        "criterio": {
            "limite_pct": float(limite_pct),
            "origen": "configurable_por_usuario",
            "normativo_universal": False,
        },
        "alimentadores": rows,
        "buses": buses,
        "resumen": {
            "alimentadores_evaluados": len(rows),
            "alimentadores_que_exceden": len(exceeded),
            "peor_alimentador_id": worst.get("id") if worst else None,
            "peor_caida_pct": worst.get("caida_evaluada_pct") if worst else None,
            "vpu_min_sistema": round(min(vmins), 4) if vmins else None,
        },
        "flow": flow,
        "metodologia": (
            "Diferencia de magnitudes de tensión pu entre bus1 y bus2 de cada Line, "
            "reportando promedio firmado y máxima caída positiva entre fases disponibles."
        ),
    }
