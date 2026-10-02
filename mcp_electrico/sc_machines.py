"""Explicit machine sheets for balanced initial three-phase fault current.

These sheets enrich existing DSS elements only for the 3F projection. A Load
is not a motor until identified; its operating kW are never treated as rated
shaft power. The default Vsource can represent a synchronous generator, in
which case its ext_grid equivalent is REPLACED, never added a second time.
"""
from __future__ import annotations

from copy import deepcopy
from math import isfinite, isclose
from typing import Any

import pandapower as pp
from opendssdirect import dss

_circuit = ""
_loads: dict[str, dict] = {}
_generators: dict[str, dict] = {}


def _circuit_name() -> str:
    try:
        return str(dss.Circuit.Name() or "")
    except Exception:
        return ""


def reset() -> None:
    global _circuit
    _circuit = _circuit_name()
    _loads.clear()
    _generators.clear()


def snapshot() -> dict:
    if _circuit_name() != _circuit:
        reset()
    return {"schema": "MCP_ELECTRICO_SC3_MACHINES_V1",
            "loads": deepcopy(sorted(_loads.values(), key=lambda r: r["element"].lower())),
            "generators": deepcopy(sorted(_generators.values(), key=lambda r: r["element"].lower()))}


def _element(element: str, classes: set[str]) -> tuple[str, str]:
    snapshot()
    full = str(element).strip()
    if "." not in full or full.split(".")[0].lower() not in classes:
        raise ValueError("SCM001: indicar el elemento completo y de clase admitida.")
    names = {n.lower(): n for n in dss.Circuit.AllElementNames()}
    if full.lower() not in names:
        raise ValueError(f"SCM002: elemento inexistente: {full}.")
    dss.Circuit.SetActiveElement(names[full.lower()])
    if dss.CktElement.NumPhases() != 3:
        raise ValueError("SCM003: las fichas 3F exigen elementos trifásicos.")
    return names[full.lower()], dss.CktElement.BusNames()[0].split(".")[0].lower()


def _number(name: str, value: float, *, zero: bool = False, maximum: float | None = None) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"SCM004: {name} debe ser numérico y finito.") from None
    if isinstance(value, bool) or not isfinite(v) or (v < 0 if zero else v <= 0) or (maximum is not None and v > maximum):
        raise ValueError(f"SCM004: {name} fuera de rango.")
    return v


def _reference(reference: str) -> str:
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError("SCM005: falta referencia de ficha o supuesto explícito; no se asignan valores típicos.")
    return reference.strip()


def clasificar_carga(elemento_carga: str, tipo: str, referencia: str) -> dict:
    """Static loads contribute zero; VFD is identified but not approximated."""
    full, bus = _element(elemento_carga, {"load"})
    kind = str(tipo).strip().upper()
    if kind not in {"ESTATICA", "VARIADOR_NO_MODELADO"}:
        raise ValueError("SCM006: usar ESTATICA o VARIADOR_NO_MODELADO; para inducción directa registrar su ficha.")
    record = {"element": full, "bus": bus, "kind": kind, "reference": _reference(referencia)}
    _loads[full.lower()] = record
    return deepcopy(record)


def definir_motor(elemento_carga: str, pn_mecanica_mw: float, vn_kv: float,
                  eficiencia_nominal_pct: float, fp_nominal: float, corriente_rotor_bloqueado_pu: float,
                  relacion_r_x: float, referencia: str) -> dict:
    full, bus = _element(elemento_carga, {"load"})
    record = {"element": full, "bus": bus, "kind": "INDUCCION_DIRECTA",
              "pn_mech_mw": _number("pn_mecanica_mw", pn_mecanica_mw),
              "vn_kv": _number("vn_kv", vn_kv),
              "efficiency_n_percent": _number("eficiencia_nominal_pct", eficiencia_nominal_pct, maximum=100),
              "cos_phi_n": _number("fp_nominal", fp_nominal, maximum=1),
              "lrc_pu": _number("corriente_rotor_bloqueado_pu", corriente_rotor_bloqueado_pu),
              "rx": _number("relacion_r_x", relacion_r_x, zero=True),
              "reference": _reference(referencia)}
    if record["lrc_pu"] < 1:
        raise ValueError("SCM007: corriente de rotor bloqueado debe ser >=1 pu nominal.")
    record["rated_sn_mva"] = record["pn_mech_mw"] / (record["efficiency_n_percent"] / 100 * record["cos_phi_n"])
    record["z_locked_rotor_ohm"] = record["vn_kv"] ** 2 / (record["rated_sn_mva"] * record["lrc_pu"])
    _loads[full.lower()] = record
    return deepcopy(record)


def definir_generador(elemento: str, sn_mva: float, vn_kv: float, xdss_pu: float,
                      rdss_ohm: float, fp_nominal: float, pg_percent: float, referencia: str,
                      transformador_unidad: str | None = None, oltc: bool | None = None,
                      pt_percent: float | None = None) -> dict:
    full, bus = _element(elemento, {"vsource", "generator"})
    if full.lower().startswith("vsource.") and full.lower() != "vsource.source":
        raise ValueError("SCM008: solo Vsource.source admite sustitución por generador síncrono.")
    record = {"element": full, "bus": bus, "kind": "SINCRONO",
              "sn_mva": _number("sn_mva", sn_mva), "vn_kv": _number("vn_kv", vn_kv),
              "xdss_pu": _number("xdss_pu", xdss_pu), "rdss_ohm": _number("rdss_ohm", rdss_ohm, zero=True),
              "cos_phi": _number("fp_nominal", fp_nominal, maximum=1),
              "pg_percent": _number("pg_percent", pg_percent, zero=True),
              "reference": _reference(referencia), "unit_transformer": None}
    if transformador_unidad is not None:
        from . import professional_data
        trafo = professional_data.obtener_transformador(transformador_unidad)
        if not trafo or str(trafo["buses"]["lv"]).lower() != bus:
            raise ValueError("SCM009: la unidad exige ficha P2 de un transformador con LV en la barra del generador.")
        if not isinstance(oltc, bool) or pt_percent is None:
            raise ValueError("SCM010: declarar explícitamente OLTC y pt_percent de la unidad; cero solo si corresponde.")
        record["unit_transformer"] = trafo["id"]
        record["oltc"] = oltc
        record["pt_percent"] = _number("pt_percent", pt_percent, zero=True, maximum=50)
        if any(g.get("unit_transformer", "").lower() == trafo["id"].lower() for k, g in _generators.items()
               if k != full.lower() and g.get("unit_transformer")):
            raise ValueError("SCM011: solo una máquina por unidad generador-transformador.")
    elif oltc is not None or pt_percent is not None:
        raise ValueError("SCM010: OLTC/pt_percent requieren transformador_unidad.")
    _generators[full.lower()] = record
    return deepcopy(record)


def eliminar_ficha(elemento: str) -> dict:
    snapshot()
    key = str(elemento).strip().lower()
    old = _loads.pop(key, None) or _generators.pop(key, None)
    if old is None:
        raise ValueError("SCM012: ficha inexistente.")
    return {"removed": old, "requires_new_review": True}


def _state(record: dict) -> dict:
    full = record["element"]
    exists = full.lower() in {n.lower() for n in dss.Circuit.AllElementNames()}
    if exists:
        dss.Circuit.SetActiveElement(full)
    return {**deepcopy(record), "exists": exists,
            "enabled": bool(dss.CktElement.Enabled()) if exists else False,
            "open": any(dss.CktElement.IsOpen(t, 0) for t in range(1, dss.CktElement.NumTerminals()+1)) if exists else False,
            "actual_bus": dss.CktElement.BusNames()[0].split(".")[0].lower() if exists else None}


def inventory(model: dict) -> dict:
    data = snapshot()
    loads = [_state(r) for r in data["loads"]]
    gens = [_state(r) for r in data["generators"]]
    mapped = {r["element"].lower() for r in loads}
    unknown = [r for r in model["loads"] if r["id"].lower() not in mapped]
    return {"loads": loads, "generators": gens, "unclassified_loads": deepcopy(unknown),
            "extension_enabled": bool(loads or gens),
            "minimum_motor_policy": "MIN_EXCLUYE_MOTORES_INDUCCION",
            "operating_load_kw_is_rated_shaft_power": False}


def readiness(model: dict, duty: bool = False) -> tuple[dict, list[dict]]:
    inv = inventory(model)
    issues = []
    def add(code, message, element=None):
        issues.append({"code": code, "message": message, "element": element})
    buses = {b["name"].lower(): b for b in model["buses"]}
    trafos = {t["id"].lower(): t for t in model["transformers"]}
    for r in inv["loads"] + inv["generators"]:
        if not r["exists"] or r["actual_bus"] != r["bus"]:
            add("SCM101", "Ficha huérfana o barra modificada; volver a definir y revisar.", r["element"])
        if r["kind"] == "VARIADOR_NO_MODELADO" and r["enabled"] and not r["open"]:
            add("SCM102", "El variador exige modelo de convertidor y datos del fabricante; no se aproxima como motor directo ni se omite.", r["element"])
        if "vn_kv" in r:
            vn = (buses.get(r["bus"]) or {}).get("vn_kv_ll")
            if not vn or not isclose(vn, r["vn_kv"], rel_tol=1e-5):
                add("SCM103", "Tensión nominal de ficha incompatible con la barra; revisar el nivel nominal.", r["element"])
        if r.get("unit_transformer"):
            t = trafos.get(r["unit_transformer"].lower())
            if not t or not t.get("professional") or str(t["professional"]["buses"]["lv"]).lower() != r["bus"]:
                add("SCM104", "Unidad generador-transformador modificada o sin ficha P2 coherente.", r["element"])
    # Once machines are used, require an explicit disposition of every load.
    if inv["extension_enabled"]:
        for r in inv["unclassified_loads"]:
            add("SCM105", "Carga sin clasificar: declarar estática, inducción directa con ficha o variador. No inferirlo desde MW/fp.", r["id"])
    if duty and (inv["generators"] or any(r["kind"] == "INDUCCION_DIRECTA" for r in inv["loads"])):
        add("SCM106", "Esta extensión valida Ik'' inicial; ip/Ith con máquinas requieren validación de decaimiento y no se ejecutan en este alcance.")
    # K_G/K_S data structures only hold one generator per bus in this backend.
    occupied = set()
    for r in inv["generators"]:
        if r["enabled"] and not r["open"]:
            if r["bus"] in occupied:
                add("SCM107", "Generadores múltiples en una misma barra requieren validación separada.", r["element"])
            occupied.add(r["bus"])
    return inv, issues


def source_generator() -> dict | None:
    snapshot()
    return deepcopy(_generators.get("vsource.source"))


def fault_connectivity(model: dict, inv: dict, bus: str) -> list[dict]:
    """Do not promote an isolated bus or a motor-only island as a valid fault."""
    import networkx as nx
    from . import pandapower_engine
    graph = nx.Graph()
    graph.add_nodes_from(b["name"].lower() for b in model["buses"])
    for r in model["lines"]:
        if r.get("enabled", True) and not r["open"]:
            graph.add_edge(r["bus1"].lower(), r["bus2"].lower())
    for r in model["transformers"]:
        p = r.get("professional")
        if p and r.get("enabled", True) and not r["open"]:
            graph.add_edge(p["buses"]["hv"].lower(), p["buses"]["lv"].lower())
    sources = {r["bus"] for r in inv["generators"] if r["exists"] and r["enabled"] and not r["open"]}
    if model["circuit"] and not source_generator():
        dss.Circuit.SetActiveElement("Vsource.source")
        if dss.CktElement.Enabled() and not pandapower_engine._active_element_is_open("Vsource.source"):
            sources.add(str(model["source_bus"]).lower())
    key = str(bus).strip().lower()
    if key in graph and not sources.intersection(nx.node_connected_component(graph, key)):
        return [{"code": "SCM109", "message": "Barra aislada de fuentes disponibles; no se calcula ni se presenta corriente válida.", "element": bus}]
    return []


def project(net, model: dict, trafo_meta: dict) -> dict:
    """Project only SC data. No new operating loads, no duplicate source."""
    inv, issues = readiness(model)
    if issues:
        raise ValueError(str(issues))
    buses = {str(row["name"]).lower(): int(i) for i, row in net.bus.iterrows()}
    trafos = {m["id"].lower(): i for i, m in trafo_meta.items()}
    if source_generator():
        net.ext_grid.drop(net.ext_grid.index, inplace=True)
    for r in inv["generators"]:
        unit = r.get("unit_transformer")
        kwargs = {}
        if unit:
            ti = trafos[unit.lower()]
            net.trafo.at[ti, "power_station_unit"] = True
            net.trafo.at[ti, "oltc"] = r["oltc"]
            net.trafo.at[ti, "pt_percent"] = r["pt_percent"]
            kwargs["power_station_trafo"] = ti
        pp.create_gen(net, buses[r["bus"]], p_mw=0., vm_pu=1., slack=True,
                      sn_mva=r["sn_mva"], vn_kv=r["vn_kv"], xdss_pu=r["xdss_pu"],
                      rdss_ohm=r["rdss_ohm"], cos_phi=r["cos_phi"], pg_percent=r["pg_percent"],
                      name=r["element"], in_service=r["enabled"] and not r["open"], **kwargs)
    for r in inv["loads"]:
        if r["kind"] == "INDUCCION_DIRECTA":
            # Existing PQ Load is retained. It is ignored in equivalent-voltage
            # SC; this additional motor is its fault impedance, not a new demand.
            pp.create_motor(net, buses[r["bus"]], r["pn_mech_mw"], cos_phi=r["cos_phi_n"],
                            efficiency_percent=r["efficiency_n_percent"],
                            cos_phi_n=r["cos_phi_n"], efficiency_n_percent=r["efficiency_n_percent"],
                            vn_kv=r["vn_kv"], lrc_pu=r["lrc_pu"], rx=r["rx"], name=r["element"],
                            in_service=r["enabled"] and not r["open"])
    return inv


def register(mcp, on_model_change=None) -> None:
    def changed(action):
        if on_model_change:
            on_model_change(action)

    @mcp.tool()
    def definir_motor_cortocircuito_3ph(elemento_carga: str, pn_mecanica_mw: float, vn_kv: float,
                                      eficiencia_nominal_pct: float, fp_nominal: float,
                                      corriente_rotor_bloqueado_pu: float, relacion_r_x: float, referencia: str) -> dict:
        """Ficha de inducción directa para Ik'' 3F; exige potencia mecánica nominal, no consumo MW de un agregado."""
        result = definir_motor(elemento_carga, pn_mecanica_mw, vn_kv, eficiencia_nominal_pct,
                               fp_nominal, corriente_rotor_bloqueado_pu, relacion_r_x, referencia)
        changed("definir_motor_cortocircuito_3ph")
        return result

    @mcp.tool()
    def clasificar_carga_cortocircuito_3ph(elemento_carga: str, tipo: str, referencia: str) -> dict:
        """Clasifica ESTATICA o VARIADOR_NO_MODELADO. El variador bloquea cálculo; no se supone aporte cero."""
        result = clasificar_carga(elemento_carga, tipo, referencia)
        changed("clasificar_carga_cortocircuito_3ph")
        return result

    @mcp.tool()
    def definir_generador_cortocircuito_3ph(elemento: str, sn_mva: float, vn_kv: float,
                                          xdss_pu: float, rdss_ohm: float, fp_nominal: float,
                                          pg_percent: float, referencia: str,
                                          transformador_unidad: str | None = None,
                                          oltc: bool | None = None, pt_percent: float | None = None) -> dict:
        """Generador síncrono IEC con Xd'', R y K_G/K_S. Vsource.source sustituye al equivalente; no se suman ambos."""
        result = definir_generador(elemento, sn_mva, vn_kv, xdss_pu, rdss_ohm, fp_nominal,
                                   pg_percent, referencia, transformador_unidad, oltc, pt_percent)
        changed("definir_generador_cortocircuito_3ph")
        return result

    @mcp.tool()
    def obtener_fichas_maquinas_cortocircuito_3ph() -> dict:
        """Devuelve fichas explícitas, estado actual y cargas sin clasificar; no resuelve la red."""
        from . import pandapower_engine
        inv, issues = readiness(pandapower_engine._collect_active_model())
        return {**inv, "issues": issues, "supported_fault": "3ph", "supported_current": "Ikss",
                "peak_thermal_with_machines": False, "protection_validation_supported": False}

    @mcp.tool()
    def eliminar_ficha_maquina_cortocircuito_3ph(elemento: str) -> dict:
        """Retira ficha de máquina/clasificación y exige nueva revisión antes de cálculo."""
        result = eliminar_ficha(elemento)
        changed("eliminar_ficha_maquina_cortocircuito_3ph")
        return result
