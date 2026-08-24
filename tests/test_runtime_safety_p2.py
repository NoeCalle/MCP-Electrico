import pytest

from mcp_electrico import (
    conductor_library,
    core,
    professional_data,
    runtime_safety,
    zero_sequence,
)


def _source():
    professional_data.definir_red_equivalente(
        kv_ll=22.9,
        scc_max_mva=500,
        x_r_max=10,
        scc_min_mva=250,
        x_r_min=7,
        fuente_referencia="estudio cc",
    )


def test_crear_circuito_reinicia_estados_p2_aunque_reutilice_el_mismo_nombre():
    runtime_safety.install()
    core.crear_circuito("same_name_p2", 22.9)
    _source()
    zero_sequence.definir_fuente(0.3, 0.9, 0.5, 1.2)
    core.agregar_linea("l1", "sourcebus", "b1", 0.1, r1_ohm_km=0.2, x1_ohm_km=0.08)
    conductor_library.aplicar_conductor(
        "Line.l1", "NEXANS-N2XSY-18-30-CU-70-PH16", "air_trefoil"
    )

    assert professional_data.obtener_red_equivalente() is not None
    assert zero_sequence.obtener_fuente() is not None
    assert conductor_library.obtener_asignacion("Line.l1") is not None

    # Reutilizar el mismo nombre no puede conservar estado profesional previo.
    core.crear_circuito("same_name_p2", 22.9)

    assert professional_data.obtener_red_equivalente() is None
    assert zero_sequence.obtener_fuente() is None
    assert conductor_library.obtener_asignacion("Line.l1") is None


def test_faultstudy_legacy_sigue_disponible_sin_contexto_p2():
    runtime_safety.install()
    core.crear_circuito("legacy_faultstudy", 22.9)
    core.agregar_linea("l1", "sourcebus", "b1", 0.1, r1_ohm_km=0.2, x1_ohm_km=0.08)

    preflight = runtime_safety.evaluar_faultstudy_opendss()
    assert preflight["professional_context"] is False
    assert preflight["ready"] is True

    result = core.ejecutar_cortocircuito("b1")
    assert result["bus"] == "b1"


def test_faultstudy_p2_bloquea_z0_obsoleta_al_cambiar_escenario():
    runtime_safety.install()
    core.crear_circuito("p2_fault_stale", 22.9)
    _source()
    core.agregar_linea("l1", "sourcebus", "b1", 0.1, r1_ohm_km=0.2, x1_ohm_km=0.08)
    zero_sequence.definir_linea("l1", 0.65, 0.32)
    zero_sequence.definir_fuente(0.3, 0.9)  # solo máximo

    professional_data.seleccionar_escenario_red("min")
    zero_sequence.reapply_active_source()

    preflight = runtime_safety.evaluar_faultstudy_opendss()
    assert preflight["professional_context"] is True
    assert preflight["ready"] is False
    assert any(r["code"] == "P2ZFAULT012" for r in preflight["reasons"])

    with pytest.raises(ValueError, match="P2ZFAULT001"):
        core.ejecutar_cortocircuito("b1")


def test_faultstudy_p2_bloquea_transformador_z0_no_proyectable_a_opendss():
    runtime_safety.install()
    core.crear_circuito("p2_fault_transformer", 22.9)
    _source()
    zero_sequence.definir_fuente(0.3, 0.9, 0.5, 1.2)
    professional_data.agregar_transformador_profesional(
        nombre="tr1",
        bus_hv="sourcebus",
        bus_lv="lvbus",
        kva=1000,
        kv_hv=22.9,
        kv_lv=0.48,
        uk_percent=6.0,
        grupo_vectorial="Dyn11",
        x_r=10.0,
        no_load_loss_kw=2.0,
        i0_percent=0.8,
        fuente_referencia="ficha tecnica",
    )
    zero_sequence.definir_transformador(
        "tr1",
        uk0_percent=5.5,
        ur0_percent=0.6,
        magnetizing_z0_ratio_percent=100.0,
        magnetizing_r_over_x=0.0,
        leakage_share_hv=0.5,
        neutral_side="lv",
        neutral_mode="solid",
    )

    preflight = runtime_safety.evaluar_faultstudy_opendss()
    assert preflight["ready"] is False
    assert any(r["code"] == "P2ZFAULT031" for r in preflight["reasons"])

    with pytest.raises(ValueError, match="P2ZFAULT031"):
        core.ejecutar_cortocircuito("lvbus")
