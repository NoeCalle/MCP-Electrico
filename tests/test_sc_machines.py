"""Independent impedance benchmarks and state/approval regressions for SC3.

References use equivalent-voltage impedances and complex parallel/series
algebra, without calling pandapower to construct the expected currents.
"""
from math import sqrt

import pytest
from opendssdirect import dss

import server
from mcp_electrico import (core, iec60909, professional_data, sc_machines as machines,
                          short_circuit_precheck as gate, project_snapshot, workspace_state)


@pytest.fixture
def circuit():
    core.crear_circuito("sc_machine_benchmark", 13.8, 60.)
    professional_data.definir_red_equivalente(13.8, 500., 10., 250., 5., fuente_referencia="Synthetic benchmark")
    core.agregar_carga("motor", "sourcebus", 500., 200., fases=3, kv=13.8)
    return "sourcebus"


def motor():
    return machines.definir_motor("Load.motor", .8, 13.8, 95., .9, 6., .1, "Synthetic rated motor sheet")


def gen(unit=None, oltc=None, pt=None, element="Vsource.source"):
    return machines.definir_generador(element, 37.5, 13.8, .2, .03, .8, 0., "Synthetic generator sheet", unit, oltc, pt)


def review(p):
    return {"model_sha256": p["model_sha256"], "uso_previsto": p["supported_scope"],
            "calidad_datos": "SUPUESTOS_APROBADOS", "referencia_revision": "Synthetic module benchmark, not a project design approval",
            "supuestos_aprobados": ["All fixture inputs are explicit illustrative numerical test values."],
            "exclusiones_revisadas": [r["id"] for r in p["items_to_review"]]}


def impedance(magnitude, rx):
    x = magnitude / sqrt(1 + rx**2)
    return complex(rx*x, x)


@pytest.mark.parametrize("hz", [50., 60.])
def test_utility_and_motor_complex_parallel_benchmark(circuit, hz):
    dss(f"set frequency={hz}")
    m = motor()
    zm = impedance(13.8**2 / (.8/.95/.9*6), .1)
    ze = impedance(1.1 * 13.8**2 / 500., .1)
    expected = 1.1 * 13.8 / sqrt(3) * abs(1/ze + 1/zm)
    result = gate.ejecutar_revisado(circuit, revision_modelo=review(gate.evaluar(circuit)))
    assert result["ok"], result
    assert result["scenarios"]["max"]["results"]["ikss_ka"] == pytest.approx(expected, rel=1e-8)
    assert result["scenarios"]["min"]["results"]["ikss_ka"] == pytest.approx(250./sqrt(3)/13.8, rel=1e-8)
    assert m["rated_sn_mva"] == pytest.approx(.8/.95/.9)
    assert result["result_scope"] == gate.MACHINE_SCOPE
    assert not result["protection_validation_supported"]


@pytest.mark.parametrize("case,c", [("max",1.1), ("min",1.)])
@pytest.mark.parametrize("with_motor", [False, True])
def test_synchronous_generator_island_kg_and_no_duplicate_source(circuit, case, c, with_motor):
    if with_motor:
        motor()
    else:
        machines.clasificar_carga("Load.motor", "ESTATICA", "Synthetic static demand")
    gen()
    # Registered P2 source500MVA must NOT contribute in this configuration.
    zg = complex(.03, .2 * 13.8**2 / 37.5)
    kg = 1.1 / (1 + .2 * sqrt(1-.8**2))
    y = 1/(kg*zg)
    if with_motor and case == "max":
        y += 1/impedance(13.8**2/(.8/.95/.9*6), .1)
    expected = c * 13.8 / sqrt(3) * abs(y)
    result = iec60909.ejecutar_3ph(case, circuit)
    assert result["ok"], result
    assert result["results"]["ikss_ka"] == pytest.approx(expected, rel=1e-8)
    assert result["machine_extension"]["source_equivalent_replaced_by_synchronous_generator"]


@pytest.mark.parametrize("oltc", [False, True])
def test_generator_transformer_unit_external_fault_and_terminal_currents(circuit, oltc):
    machines.clasificar_carga("Load.motor", "ESTATICA", "Static benchmark demand")
    t = professional_data.agregar_transformador_profesional(
        "tgen", "hv", "sourcebus", 40000., 138., 13.8, 10., "Yy0",
        x_r=10., no_load_loss_kw=40., i0_percent=.5, fuente_referencia="Synthetic transformer")
    gen("Transformer.tgen", oltc, 0.)
    # Nominal transformer impedance referred to HV; K_T must not be applied
    # independently when generator and transformer form a power station unit.
    zt = impedance(.1 * 138.**2 / 40., .1)
    zg = complex(.03, .2*13.8**2/37.5) * (138./13.8)**2
    xt = zt.imag / (138.**2 / 40.)
    ks = 1.1 / (1 + (abs(.2-xt) if oltc else .2) * .6)
    expected = 1.1 * 138. / sqrt(3) / abs(ks*(zt+zg))
    r = iec60909.ejecutar_3ph("max", "hv")
    assert r["ok"], r
    assert r["results"]["ikss_ka"] == pytest.approx(expected, rel=2e-5)
    b = r["branch_results"]["transformers"][0]
    assert b["ikss_hv_ka"] == pytest.approx(expected, rel=2e-5)
    assert b["ikss_lv_ka"] == pytest.approx(expected*10., rel=2e-5)


def test_cable_transmits_total_fault_but_motor_changes_source_branch_current(circuit):
    # Move motor to receiving bus; cable sees utility contribution, whereas
    # fault current also includes the local motor's complex contribution.
    core.agregar_linea("cable", "sourcebus", "loadbus", 1., fases=3, r1_ohm_km=.3, x1_ohm_km=.4)
    dss("edit Load.motor bus1=loadbus.1.2.3")
    motor()
    ze = impedance(1.1*13.8**2/500., .1) + complex(.3,.4)
    zm = impedance(13.8**2/(.8/.95/.9*6), .1)
    expected_source = 1.1*13.8/sqrt(3)/abs(ze)
    expected_total = 1.1*13.8/sqrt(3)*abs(1/ze+1/zm)
    r = iec60909.ejecutar_3ph("max", "loadbus")
    assert r["ok"], r
    assert r["results"]["ikss_ka"] == pytest.approx(expected_total, rel=1e-8)
    b = r["branch_results"]["lines"][0]
    assert b["ikss_from_ka"] == pytest.approx(expected_source, rel=1e-8)
    assert b["ikss_to_ka"] == pytest.approx(expected_source, rel=1e-8)
    assert b["ikss_to_ka"] < r["results"]["ikss_ka"]


@pytest.mark.parametrize("mutation", ["disable", "open"])
def test_disconnected_motor_does_not_contribute_and_stales_review(circuit, mutation):
    motor()
    p = gate.evaluar(circuit)
    dss("edit Load.motor enabled=no" if mutation == "disable" else "open Load.motor term=1")
    stale = gate.ejecutar_revisado(circuit, revision_modelo=review(p))
    assert not stale["electrical_calculation_executed"]
    assert "SCREV003" in [i["code"] for i in stale["issues"]]
    r = iec60909.ejecutar_3ph("max", circuit)
    assert r["ok"], r
    assert r["results"]["ikss_ka"] == pytest.approx(500/sqrt(3)/13.8, rel=1e-8)


def test_unclassified_load_and_vfd_block_before_solver(circuit, monkeypatch):
    motor()
    core.agregar_carga("unknown", circuit, 10., 2., fases=3, kv=13.8)
    monkeypatch.setattr(iec60909, "calc_sc", lambda *a, **k: pytest.fail("Unreviewed machine calculation"))
    p = gate.evaluar(circuit)
    assert not p["numerical_ready"]
    assert "SCM105" in [i["code"] for i in p["numeric_readiness"]["max"]["issues"]]
    machines.clasificar_carga("Load.unknown", "VARIADOR_NO_MODELADO", "VFD manufacturer sheet pending")
    p = gate.evaluar(circuit)
    assert "SCM102" in [i["code"] for i in p["numeric_readiness"]["max"]["issues"]]
    assert not gate.ejecutar_revisado(circuit, revision_modelo=review(p))["electrical_calculation_executed"]


def test_ip_ith_with_machines_is_explicitly_blocked(circuit):
    motor()
    p = gate.evaluar(circuit, calcular_ip_ith=True, topology="radial", tk_s=.2)
    assert not p["numerical_ready"]
    assert "SCM106" in [i["code"] for i in p["numeric_readiness"]["max"]["issues"]]


def test_machine_data_and_source_state_bind_review(circuit):
    motor()
    p = gate.evaluar(circuit)
    machines.definir_motor("Load.motor", .9, 13.8, 95., .9, 6., .1, "Changed fixture")
    assert "SCREV003" in [i["code"] for i in gate.validar_revision(gate.evaluar(circuit), review(p))]
    p = gate.evaluar(circuit)
    dss("edit Vsource.source enabled=no")
    assert "SCREV003" in [i["code"] for i in gate.validar_revision(gate.evaluar(circuit), review(p))]


def test_machine_bus_mutation_and_rating_mismatch_block(circuit):
    core.agregar_linea("link", circuit, "other", .1, fases=3, r1_ohm_km=.1, x1_ohm_km=.1)
    motor()
    dss("edit Load.motor bus1=other.1.2.3")
    p = gate.evaluar(circuit, {"Line.link":20.})
    assert "SCM101" in [i["code"] for i in p["numeric_readiness"]["max"]["issues"]]
    machines.definir_motor("Load.motor", .8, 4.16, 95., .9, 6., .1, "Wrong voltage fixture")
    p = gate.evaluar("other", {"Line.link":20.})
    assert "SCM103" in [i["code"] for i in p["numeric_readiness"]["max"]["issues"]]


def test_machine_sheets_exported_and_same_name_new_circuit_resets(circuit, tmp_path):
    motor(); gen()
    s = project_snapshot.construir_snapshot(str(tmp_path/"netlist"))
    sheets = s["payload"]["engineering_data"]["sc3_machine_sheets"]
    assert sheets["loads"][0]["kind"] == "INDUCCION_DIRECTA"
    assert sheets["generators"][0]["xdss_pu"] == .2
    assert project_snapshot.verificar_snapshot(s)["ok"]
    core.crear_circuito("sc_machine_benchmark", 13.8, 60.)
    assert machines.snapshot()["loads"] == []
    assert machines.snapshot()["generators"] == []


@pytest.mark.parametrize("value", [0., -1., float("nan"), float("inf"), True])
def test_invalid_machine_sheet_is_atomic(circuit, value):
    before = machines.snapshot()
    with pytest.raises(ValueError, match="SCM004"):
        machines.definir_motor("Load.motor", value, 13.8, 95., .9, 6., .1, "Bad data")
    assert machines.snapshot() == before


def test_generator_transformer_parameters_require_explicit_unit(circuit):
    with pytest.raises(ValueError, match="SCM010"):
        gen(None, False, 0.)
    with pytest.raises(ValueError, match="SCM009"):
        gen("Transformer.absent", False, 0.)


def test_non3ph_and_flow_do_not_silently_omit_machine_model(circuit):
    from mcp_electrico import pandapower_engine, iec60909_two_phase
    motor()
    assert not pandapower_engine.ejecutar_flujo()["ok"]
    p = iec60909_two_phase.evaluar_preparacion_2ph("max", circuit)
    assert not p["ready"]
    assert "PP013" in [i["code"] for i in p["issues"]]


def test_public_tools_register_and_invalidate_current_study(circuit):
    import asyncio
    workspace_state.reset_for_circuit("synthetic")
    asyncio.run(server.mcp.call_tool("definir_motor_cortocircuito_3ph", {
        "elemento_carga": "Load.motor", "pn_mecanica_mw": .8, "vn_kv":13.8,
        "eficiencia_nominal_pct":95., "fp_nominal":.9, "corriente_rotor_bloqueado_pu":6.,
        "relacion_r_x":.1, "referencia":"Synthetic MCP tool"}))
    p = server.evaluar_preparacion_cortocircuito_3ph(circuit)
    r = server.ejecutar_cortocircuito_iec60909_3ph(circuit, revision_modelo=review(p))
    assert r["ok"], r
    assert workspace_state.status()["studies"]["iec60909_3ph"]["valid"]
    asyncio.run(server.mcp.call_tool("eliminar_ficha_maquina_cortocircuito_3ph", {"elemento":"Load.motor"}))
    assert not workspace_state.status()["studies"]["iec60909_3ph"]["valid"]


def test_native_generator_and_utility_parallel_benchmark(circuit):
    machines.clasificar_carga("Load.motor", "ESTATICA", "Synthetic static demand")
    core.agregar_linea("gencable", circuit, "genbus", .1, fases=3, r1_ohm_km=.3, x1_ohm_km=.4)
    dss("new Generator.realgen bus1=genbus.1.2.3 phases=3 kv=13.8 kw=1000 pf=0.8")
    gen(element="Generator.realgen")
    ze = impedance(1.1*13.8**2/500, .1) + complex(.03,.04)
    zg = complex(.03, .2*13.8**2/37.5) * (1.1/(1+.2*.6))
    expected = 1.1*13.8/sqrt(3)*abs(1/ze+1/zg)
    r = iec60909.ejecutar_3ph("max", "genbus")
    assert r["ok"], r
    assert r["results"]["ikss_ka"] == pytest.approx(expected, rel=1e-8)
    assert not r["machine_extension"]["source_equivalent_replaced_by_synchronous_generator"]


def test_generator_without_utility_equivalent_sheet_and_disabled_source(circuit):
    professional_data.reset()
    machines.clasificar_carga("Load.motor", "ESTATICA", "Synthetic static demand")
    gen()
    assert gate.evaluar(circuit)["numerical_ready"]
    assert iec60909.ejecutar_3ph("max", circuit)["ok"]
    dss("open Vsource.source term=1")
    p = gate.evaluar(circuit)
    assert not p["numerical_ready"]
    assert "SCM109" in [i["code"] for i in p["numeric_readiness"]["max"]["issues"]]


def test_open_second_terminal_isolates_fault_before_calculation(circuit, monkeypatch):
    core.agregar_linea("cable", circuit, "loadbus", .1, fases=3, r1_ohm_km=.1, x1_ohm_km=.1)
    dss("open Line.cable term=2")
    monkeypatch.setattr(iec60909, "calc_sc", lambda *a, **k: pytest.fail("Isolated fault calculation"))
    p = gate.evaluar("loadbus", {"Line.cable": 20.})
    assert not p["numerical_ready"]
    assert "SCM109" in [i["code"] for i in p["numeric_readiness"]["max"]["issues"]]


def test_workspace_shows_machine_scope_and_branch_current(circuit):
    from mcp_electrico import workspace_p4_view
    core.agregar_linea("cable", circuit, "loadbus", .1, fases=3, r1_ohm_km=.1, x1_ohm_km=.1)
    motor()
    args = {"bus_falla":"loadbus", "line_endtemp_degree_c":{"Line.cable":20.}}
    p = gate.evaluar(**args)
    r = gate.ejecutar_revisado(**args, revision_modelo=review(p))
    assert r["ok"]
    html = workspace_p4_view._study_block("iec60909_3ph", r)
    assert "máquinas declaradas" in html
    assert "Corrientes por rama" in html
    assert "Line.cable" in html
    assert "cargas Load sin aporte de motor" not in html
