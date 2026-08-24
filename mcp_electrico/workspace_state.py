"""Estado persistente del workspace y snapshot estructurado del circuito.

Este módulo NO renderiza HTML y NO modifica el modelo eléctrico. Su función es
mantener la trazabilidad entre revisiones del modelo y resultados calculados,
y exponer un snapshot serializable que actúa como contrato entre MCP Eléctrico
y cualquier interfaz visual futura.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from opendssdirect import dss

from . import professional_data, visual_state
from .core import listar_cargas_criticas

STATE_EMPTY = "EMPTY"
STATE_MODIFIED = "MODIFIED"
STATE_SOLVED = "SOLVED"
STATE_ERROR = "ERROR"

_runtime: dict[str, Any] = {
    "circuit_name": "",
    "state": STATE_EMPTY,
    "model_revision": 0,
    "solved_revision": None,
    "visual_revision": 0,
    "last_action": None,
    "last_update": None,
    "electrical_error": None,
    "workspace_error": None,
    "studies": {},
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _active_circuit_name() -> str:
    try:
        return str(dss.Circuit.Name() or "")
    except Exception:
        return ""


def _ensure_circuit_sync() -> None:
    current = _active_circuit_name()
    if current != _runtime["circuit_name"]:
        reset_for_circuit("cambio_circuito_detectado")


def reset_for_circuit(action: str = "crear_circuito") -> dict[str, Any]:
    """Reinicia el estado lógico para el circuito actualmente activo."""
    current = _active_circuit_name()
    _runtime.update(
        {
            "circuit_name": current,
            "state": STATE_MODIFIED if current else STATE_EMPTY,
            "model_revision": 1 if current else 0,
            "solved_revision": None,
            "visual_revision": 0,
            "last_action": action,
            "last_update": _now(),
            "electrical_error": None,
            "workspace_error": None,
            "studies": {},
        }
    )
    return status()


def mark_model_changed(action: str) -> dict[str, Any]:
    """Incrementa la revisión y marca los resultados previos como obsoletos."""
    _ensure_circuit_sync()
    if not _runtime["circuit_name"]:
        return status()
    _runtime["model_revision"] += 1
    _runtime["state"] = STATE_MODIFIED
    _runtime["last_action"] = action
    _runtime["last_update"] = _now()
    _runtime["electrical_error"] = None
    return status()


def mark_visual_changed(action: str) -> dict[str, Any]:
    """Registra un cambio de representación sin invalidar la solución eléctrica."""
    _ensure_circuit_sync()
    _runtime["visual_revision"] += 1
    _runtime["last_action"] = action
    _runtime["last_update"] = _now()
    return status()


def record_solution(
    result: dict[str, Any],
    study: str = "powerflow",
    action: str = "resolver_modelo",
) -> dict[str, Any]:
    """Registra una solución asociada exactamente a la revisión actual."""
    _ensure_circuit_sync()
    converged = bool(result.get("convergio", True))
    _runtime["studies"][study] = {
        "model_revision": _runtime["model_revision"],
        "recorded_at": _now(),
        "result": deepcopy(result),
    }
    _runtime["solved_revision"] = _runtime["model_revision"] if converged else None
    _runtime["state"] = STATE_SOLVED if converged else STATE_ERROR
    _runtime["last_action"] = action
    _runtime["last_update"] = _now()
    _runtime["electrical_error"] = None if converged else "La solución eléctrica no convergió."
    return status()


def record_study(name: str, result: dict[str, Any], action: str | None = None) -> dict[str, Any]:
    """Guarda un estudio sin afirmar que reemplaza al flujo de potencia base."""
    _ensure_circuit_sync()
    _runtime["studies"][name] = {
        "model_revision": _runtime["model_revision"],
        "recorded_at": _now(),
        "result": deepcopy(result),
    }
    _runtime["last_action"] = action or name
    _runtime["last_update"] = _now()
    return status()


def record_electrical_error(message: str, action: str = "electrical_error") -> dict[str, Any]:
    _ensure_circuit_sync()
    _runtime["state"] = STATE_ERROR
    _runtime["electrical_error"] = str(message)
    _runtime["last_action"] = action
    _runtime["last_update"] = _now()
    return status()


def record_workspace_error(message: str) -> dict[str, Any]:
    """Registra un fallo de UI sin alterar la validez del estado eléctrico."""
    _ensure_circuit_sync()
    _runtime["workspace_error"] = str(message)
    _runtime["last_update"] = _now()
    return status()


def clear_workspace_error() -> None:
    _runtime["workspace_error"] = None


def status() -> dict[str, Any]:
    studies = {}
    for name, item in _runtime["studies"].items():
        studies[name] = {
            **deepcopy(item),
            "valid": item["model_revision"] == _runtime["model_revision"],
        }
    return {
        **{k: deepcopy(v) for k, v in _runtime.items() if k != "studies"},
        "results_current": (
            _runtime["state"] == STATE_SOLVED
            and _runtime["solved_revision"] == _runtime["model_revision"]
        ),
        "studies": studies,
    }


def _bus_name(raw: str) -> str:
    return str(raw).split(".")[0]


def _is_open(full_name: str) -> bool:
    try:
        if not dss.Circuit.SetActiveElement(full_name):
            return False
        return bool(dss.CktElement.IsOpen(1, 0))
    except Exception:
        return False


def _collect_lines() -> list[dict[str, Any]]:
    items = []
    for name in dss.Lines.AllNames():
        dss.Lines.Name(name)
        full = f"Line.{name}"
        items.append(
            {
                "id": full,
                "name": name,
                "bus1": _bus_name(dss.Lines.Bus1()),
                "bus2": _bus_name(dss.Lines.Bus2()),
                "length": float(dss.Lines.Length()),
                "r1": float(dss.Lines.R1()),
                "x1": float(dss.Lines.X1()),
                "open": _is_open(full),
                "visual": visual_state.get_feeder(full),
            }
        )
    return items


def _collect_transformers() -> list[dict[str, Any]]:
    items = []
    for name in dss.Transformers.AllNames():
        dss.Transformers.Name(name)
        full = f"Transformer.{name}"
        buses = [_bus_name(b) for b in dss.CktElement.BusNames()]
        windings = []
        for wdg in (1, 2):
            try:
                dss.Transformers.Wdg(wdg)
                windings.append(
                    {
                        "winding": wdg,
                        "kv": float(dss.Transformers.kV()),
                        "kva": float(dss.Transformers.kVA()),
                        "connection": "delta" if bool(dss.Transformers.IsDelta()) else "wye",
                    }
                )
            except Exception:
                pass
        items.append(
            {
                "id": full,
                "name": name,
                "buses": buses,
                "windings": windings,
                "open": _is_open(full),
                "professional": professional_data.obtener_transformador(full),
            }
        )
    return items


def _collect_loads() -> list[dict[str, Any]]:
    critical = {name.lower() for name in listar_cargas_criticas()}
    items = []
    for name in dss.Loads.AllNames():
        dss.Loads.Name(name)
        buses = dss.CktElement.BusNames()
        items.append(
            {
                "id": f"Load.{name}",
                "name": name,
                "bus": _bus_name(buses[0]) if buses else "",
                "kw": float(dss.Loads.kW()),
                "kvar": float(dss.Loads.kvar()),
                "critical": name.lower() in critical,
                "visual_type": visual_state.get_load_type(name),
                "label": visual_state.get_load_label(name),
            }
        )
    return items


def _collect_generators() -> list[dict[str, Any]]:
    items = []
    for name in dss.Generators.AllNames():
        dss.Generators.Name(name)
        buses = dss.CktElement.BusNames()
        items.append(
            {
                "id": f"Generator.{name}",
                "name": name,
                "bus": _bus_name(buses[0]) if buses else "",
                "kw": float(dss.Generators.kW()),
                "kv": float(dss.Generators.kV()),
            }
        )
    return items


def collect_model_snapshot() -> dict[str, Any]:
    """Extrae el modelo activo sin ejecutar ni modificar ningún estudio."""
    _ensure_circuit_sync()
    buses = []
    for name in dss.Circuit.AllBusNames():
        buses.append({"name": name, "visual": visual_state.get_bus(name)})
    return {
        "circuit": _runtime["circuit_name"],
        "source": professional_data.obtener_red_equivalente(),
        "buses": buses,
        "lines": _collect_lines(),
        "transformers": _collect_transformers(),
        "loads": _collect_loads(),
        "generators": _collect_generators(),
        "visual": visual_state.snapshot(),
    }


def snapshot() -> dict[str, Any]:
    """Contrato serializable completo consumido por el workspace HTML."""
    return {
        "schema_version": 2,
        "status": status(),
        "model": collect_model_snapshot(),
        "professional": professional_data.snapshot(),
    }
