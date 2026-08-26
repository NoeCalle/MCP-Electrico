"""Caso mínimo declarativo para el primer uso real de MCP Eléctrico.

Alcance V1 deliberadamente estrecho:
- radial;
- trifásico balanceado;
- una sola tensión;
- líneas y cargas PQ;
- OpenDSS explícito;
- sin transformadores, generadores, despacho automático ni cross-check.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
import re
from typing import Any

from . import engine_selection, validation_status
from .visual_state import VALID_LOAD_TYPES, VALID_PROTECTIONS

INPUT_SCHEMA = "MCP_ELECTRICO_MINIMAL_CASE_V1"
RESULT_SCHEMA = "MCP_ELECTRICO_MINIMAL_CASE_RESULT_V1"
FIXED_SCOPE = "radial_balanced_three_phase_single_voltage"
_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")


class MinimalCaseError(ValueError):
    """Entrada fuera del contrato deliberadamente limitado de V1."""


def _dict(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MinimalCaseError(f"{path} debe ser un objeto JSON.")
    return value


def _list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise MinimalCaseError(f"{path} debe ser una lista JSON.")
    return value


def _unknown(data: dict[str, Any], allowed: set[str], path: str) -> None:
    extra = sorted(set(data) - allowed)
    if extra:
        raise MinimalCaseError(f"{path} contiene campos no soportados en V1: {extra}")


def _required(data: dict[str, Any], keys: set[str], path: str) -> None:
    missing = sorted(key for key in keys if key not in data)
    if missing:
        raise MinimalCaseError(f"{path} requiere campos: {missing}")


def _name(value: Any, path: str) -> str:
    text = str(value or "").strip()
    if not _NAME_RE.fullmatch(text):
        raise MinimalCaseError(
            f"{path}='{text}' no es válido. Use letras, números, guion o guion bajo; debe iniciar con letra."
        )
    return text


def _text(value: Any, path: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise MinimalCaseError(f"{path} debe ser texto.")
    text = value.strip()
    if not text and not allow_empty:
        raise MinimalCaseError(f"{path} no puede estar vacío.")
    return text


def _number(value: Any, path: str, *, minimum: float | None = None, strict: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MinimalCaseError(f"{path} debe ser numérico.")
    number = float(value)
    if minimum is not None:
        invalid = number <= minimum if strict else number < minimum
        if invalid:
            op = ">" if strict else ">="
            raise MinimalCaseError(f"{path} debe ser {op} {minimum}.")
    return number


def _optional_positive(value: Any, path: str) -> float | None:
    if value is None:
        return None
    return _number(value, path, minimum=0.0, strict=True)


def normalizar_caso(data: dict[str, Any]) -> dict[str, Any]:
    """Valida y normaliza un caso V1; falla cerrado fuera del alcance."""
    root = _dict(data, "root")
    _unknown(root, {"schema", "project", "circuit", "lines", "loads", "study"}, "root")
    _required(root, {"schema", "project", "circuit", "lines", "loads", "study"}, "root")
    if root["schema"] != INPUT_SCHEMA:
        raise MinimalCaseError(f"schema debe ser exactamente {INPUT_SCHEMA}.")

    project = _dict(root["project"], "project")
    _unknown(project, {"id", "title", "notes"}, "project")
    _required(project, {"id", "title"}, "project")
    project_n = {
        "id": _name(project["id"], "project.id"),
        "title": _text(project["title"], "project.title"),
        "notes": _text(project.get("notes", ""), "project.notes", allow_empty=True),
    }

    circuit = _dict(root["circuit"], "circuit")
    _unknown(circuit, {"name", "base_kv_ll", "frequency_hz", "source_bus"}, "circuit")
    _required(circuit, {"name", "base_kv_ll", "frequency_hz", "source_bus"}, "circuit")
    source_bus = _name(circuit["source_bus"], "circuit.source_bus")
    if source_bus.lower() != "sourcebus":
        raise MinimalCaseError("V1 fija circuit.source_bus='sourcebus' para coincidir con el circuito OpenDSS base.")
    frequency = int(_number(circuit["frequency_hz"], "circuit.frequency_hz", minimum=0.0, strict=True))
    if frequency not in {50, 60}:
        raise MinimalCaseError("circuit.frequency_hz debe ser 50 o 60 en V1.")
    circuit_n = {
        "name": _name(circuit["name"], "circuit.name"),
        "base_kv_ll": _number(circuit["base_kv_ll"], "circuit.base_kv_ll", minimum=0.0, strict=True),
        "frequency_hz": frequency,
        "source_bus": "sourcebus",
    }

    raw_lines = _list(root["lines"], "lines")
    if not raw_lines:
        raise MinimalCaseError("lines debe contener al menos una línea.")
    line_names: set[str] = set()
    known_buses: set[str] = {"sourcebus"}
    lines_n: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_lines):
        path = f"lines[{index}]"
        line = _dict(raw, path)
        _unknown(line, {"name", "bus1", "bus2", "length_km", "r1_ohm_km", "x1_ohm_km", "visual"}, path)
        _required(line, {"name", "bus1", "bus2", "length_km", "r1_ohm_km", "x1_ohm_km"}, path)
        name = _name(line["name"], f"{path}.name")
        key = name.lower()
        if key in line_names:
            raise MinimalCaseError(f"Nombre de línea duplicado: {name}")
        line_names.add(key)
        bus1 = _name(line["bus1"], f"{path}.bus1").lower()
        bus2 = _name(line["bus2"], f"{path}.bus2").lower()
        if bus1 not in known_buses:
            raise MinimalCaseError(f"{path}.bus1='{bus1}' todavía no existe. Ordene líneas desde sourcebus hacia aguas abajo.")
        if bus2 in known_buses:
            raise MinimalCaseError(f"{path}.bus2='{bus2}' ya existe. V1 no permite lazos ni reconexiones: solo árbol radial.")
        if bus1 == bus2:
            raise MinimalCaseError(f"{path} no puede conectar un bus consigo mismo.")
        visual = _dict(line.get("visual", {}), f"{path}.visual")
        _unknown(visual, {"label", "protection", "conductor", "nominal_current_a", "breaking_capacity_ka"}, f"{path}.visual")
        protection = _text(visual.get("protection", "breaker"), f"{path}.visual.protection").lower()
        if protection not in VALID_PROTECTIONS:
            raise MinimalCaseError(f"{path}.visual.protection no válido: {protection}. Admitidos: {sorted(VALID_PROTECTIONS)}")
        lines_n.append({
            "name": name,
            "bus1": bus1,
            "bus2": bus2,
            "length_km": _number(line["length_km"], f"{path}.length_km", minimum=0.0, strict=True),
            "r1_ohm_km": _number(line["r1_ohm_km"], f"{path}.r1_ohm_km", minimum=0.0, strict=True),
            "x1_ohm_km": _number(line["x1_ohm_km"], f"{path}.x1_ohm_km", minimum=0.0),
            "visual": {
                "label": _text(visual.get("label", ""), f"{path}.visual.label", allow_empty=True),
                "protection": protection,
                "conductor": _text(visual.get("conductor", ""), f"{path}.visual.conductor", allow_empty=True),
                "nominal_current_a": _optional_positive(visual.get("nominal_current_a"), f"{path}.visual.nominal_current_a"),
                "breaking_capacity_ka": _optional_positive(visual.get("breaking_capacity_ka"), f"{path}.visual.breaking_capacity_ka"),
            },
        })
        known_buses.add(bus2)

    raw_loads = _list(root["loads"], "loads")
    if not raw_loads:
        raise MinimalCaseError("loads debe contener al menos una carga.")
    load_names: set[str] = set()
    loads_n: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_loads):
        path = f"loads[{index}]"
        load = _dict(raw, path)
        _unknown(load, {"name", "bus", "kw", "kvar", "visual"}, path)
        _required(load, {"name", "bus", "kw"}, path)
        name = _name(load["name"], f"{path}.name")
        key = name.lower()
        if key in load_names:
            raise MinimalCaseError(f"Nombre de carga duplicado: {name}")
        load_names.add(key)
        bus = _name(load["bus"], f"{path}.bus").lower()
        if bus not in known_buses:
            raise MinimalCaseError(f"{path}.bus='{bus}' no pertenece al árbol radial construido.")
        visual = _dict(load.get("visual", {}), f"{path}.visual")
        _unknown(visual, {"label", "type", "critical"}, f"{path}.visual")
        load_type = _text(visual.get("type", "tablero"), f"{path}.visual.type").lower()
        if load_type not in VALID_LOAD_TYPES:
            raise MinimalCaseError(f"{path}.visual.type no válido: {load_type}. Admitidos: {sorted(VALID_LOAD_TYPES)}")
        critical = visual.get("critical", False)
        if not isinstance(critical, bool):
            raise MinimalCaseError(f"{path}.visual.critical debe ser booleano.")
        loads_n.append({
            "name": name,
            "bus": bus,
            "kw": _number(load["kw"], f"{path}.kw", minimum=0.0, strict=True),
            "kvar": _number(load.get("kvar", 0.0), f"{path}.kvar"),
            "visual": {
                "label": _text(visual.get("label", ""), f"{path}.visual.label", allow_empty=True),
                "type": load_type,
                "critical": critical,
            },
        })

    study = _dict(root["study"], "study")
    _unknown(study, {"voltage_drop_limit_pct"}, "study")
    _required(study, {"voltage_drop_limit_pct"}, "study")
    study_n = {
        "voltage_drop_limit_pct": _number(
            study["voltage_drop_limit_pct"], "study.voltage_drop_limit_pct", minimum=0.0, strict=True
        )
    }

    return {
        "schema": INPUT_SCHEMA,
        "project": project_n,
        "circuit": circuit_n,
        "lines": lines_n,
        "loads": loads_n,
        "study": study_n,
    }


def canonical_sha256(normalized: dict[str, Any]) -> str:
    payload = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def cargar_caso(path: str | Path) -> dict[str, Any]:
    source = Path(path).expanduser().resolve()
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise MinimalCaseError(f"Archivo no encontrado: {source}") from exc
    except json.JSONDecodeError as exc:
        raise MinimalCaseError(f"JSON inválido en {source}: {exc}") from exc
    return normalizar_caso(data)


def ejecutar_caso(normalized: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    """Ejecuta un caso ya validado y genera workspace + evidencia JSON."""
    case = normalizar_caso(deepcopy(normalized))
    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    workspace_path = out / "workspace_caso_minimo.html"
    normalized_path = out / "caso_entrada_normalizado.json"
    result_path = out / "resultado_caso_minimo.json"

    digest = canonical_sha256(case)
    normalized_path.write_text(
        json.dumps(case, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    server = importlib.import_module("server")
    circuit = case["circuit"]
    server.configurar_workspace(
        str(workspace_path),
        titulo=case["project"]["title"],
        auto_regenerar=True,
    )
    server.crear_circuito(circuit["name"], circuit["base_kv_ll"], circuit["frequency_hz"])

    for line in case["lines"]:
        server.agregar_linea(
            line["name"],
            line["bus1"],
            line["bus2"],
            line["length_km"],
            fases=3,
            r1_ohm_km=line["r1_ohm_km"],
            x1_ohm_km=line["x1_ohm_km"],
        )
        visual = line["visual"]
        server.configurar_alimentador_unifilar(
            f"Line.{line['name']}",
            etiqueta=visual["label"],
            proteccion=visual["protection"],
            conductor=visual["conductor"],
            corriente_nominal_a=visual["nominal_current_a"],
            capacidad_ruptura_ka=visual["breaking_capacity_ka"],
        )

    for load in case["loads"]:
        visual = load["visual"]
        server.agregar_carga(
            load["name"],
            load["bus"],
            load["kw"],
            load["kvar"],
            fases=3,
            kv=circuit["base_kv_ll"],
            critica=visual["critical"],
            tipo_visual=visual["type"],
        )
        if visual["label"]:
            server.configurar_etiqueta_carga_unifilar(load["name"], visual["label"])

    power_flow = server.ejecutar_flujo_potencia()
    voltage_drop = server.analizar_caida_tension(case["study"]["voltage_drop_limit_pct"])
    workspace_state = server.obtener_estado_workspace()

    capabilities = engine_selection.obtener_capacidades_motores()
    engine_policy = {
        "executed_engine": "OpenDSS",
        "automatic_dispatch": capabilities.get("automatic_dispatch"),
        "crosscheck": capabilities.get("crosscheck"),
        "pandapower_executed": False,
    }
    maturity = {
        "power_flow": validation_status.get_module_status("power_flow"),
        "voltage_drop": validation_status.get_module_status("voltage_drop"),
    }
    checks = {
        "input_validated": True,
        "opendss_converged": bool(power_flow.get("convergio")),
        "voltage_drop_converged": bool(voltage_drop.get("convergio")),
        "workspace_generated": workspace_path.exists(),
        "engine_policy_preserved": engine_policy["automatic_dispatch"] is False
        and engine_policy["crosscheck"] is False
        and engine_policy["pandapower_executed"] is False,
    }
    ok = all(checks.values())

    result = {
        "schema": RESULT_SCHEMA,
        "ok": ok,
        "case_id": case["project"]["id"],
        "case_title": case["project"]["title"],
        "input_schema": INPUT_SCHEMA,
        "input_sha256": digest,
        "fixed_scope": FIXED_SCOPE,
        "checks": checks,
        "engine_policy": engine_policy,
        "maturity": maturity,
        "power_flow": power_flow,
        "voltage_drop": voltage_drop,
        "workspace_state": workspace_state,
        "counts": {
            "lines": len(case["lines"]),
            "loads": len(case["loads"]),
        },
        "outputs": {
            "normalized_input": str(normalized_path),
            "workspace_html": str(workspace_path),
            "result_json": str(result_path),
        },
        "limitations": [
            "V1 solo acepta red radial trifásica balanceada de una sola tensión.",
            "No admite transformadores, generadores, lazos, desbalance ni modelos de secuencia cero.",
            "El límite de caída de tensión es criterio configurable del caso, no una regla normativa universal.",
            "No ejecuta ampacidad normativa P3, IEC 60909, coordinación/TCC ni IEEE 1584.",
        ],
        "professional_emission": False,
    }
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return result
