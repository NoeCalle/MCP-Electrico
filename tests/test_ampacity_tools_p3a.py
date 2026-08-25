from mcp_electrico import ampacity_tools


class FakeMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn
        return decorator


def test_p3_tools_quedan_registradas_con_gate_de_evidencia():
    mcp = FakeMCP()
    ampacity_tools.register(mcp, on_study=lambda *_args, **_kwargs: None)

    assert {
        "listar_referencias_ampacidad",
        "listar_perfiles_normativos_ampacidad",
        "listar_datasets_numericos_ampacidad",
        "listar_fuentes_primarias_ampacidad",
        "verificar_archivo_fuente_ampacidad",
        "construir_evidencia_primaria_ampacidad",
        "evaluar_promocion_dataset_ampacidad",
        "resolver_factor_agrupamiento_ampacidad",
        "definir_aplicabilidad_normativa_ampacidad",
        "obtener_estado_ampacidad",
        "definir_condiciones_ampacidad",
        "evaluar_ampacidad",
    } <= set(mcp.tools)

    profiles = mcp.tools["listar_perfiles_normativos_ampacidad"]()
    by_id = {item["id"]: item for item in profiles}
    assert by_id["PERU_CNE_UTIL_2006_030_004"]["status"] == "RULE_SCHEMA_READY"
    assert by_id["IEC_60364_5_52_2009_A1_2024"]["status"] == "REFERENCE_ONLY"
    assert all(item["automatic_factor_lookup"] is False for item in profiles)

    datasets = mcp.tools["listar_datasets_numericos_ampacidad"]()
    assert len(datasets) >= 1
    assert all(item["usage_policy"]["professional_emission"] is False for item in datasets)

    sources = mcp.tools["listar_fuentes_primarias_ampacidad"]()
    assert len(sources) >= 1
    assert sources[0]["source_class"] == "OFFICIAL_PRIMARY_CANDIDATE"
    assert sources[0]["pin_status"] == "DISCOVERED_UNPINNED"
