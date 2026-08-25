from mcp_electrico import ampacity_tools


OFFICIAL_SHA256 = "2b3cbd457c519bf9d9aa2cf2754c72b6e531708e45ea2fdf91f839b1acccfd64"


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
        "evaluar_evidencia_normativa_ampacidad",
        "evaluar_cierre_p3",
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
    assert sources[0]["pin_status"] == "PINNED"
    assert sources[0]["expected_sha256"] == OFFICIAL_SHA256

    evidence = mcp.tools["evaluar_evidencia_normativa_ampacidad"]()
    assert evidence["professional_emission"] is False
    assert evidence["status"] in {
        "NOT_CONFIGURED",
        "PRIMARY_EVIDENCE_READY",
        "SECONDARY_EVIDENCE_ONLY",
        "MANUAL_EVIDENCE",
        "BASE_CONDITIONS_CONFIRMED",
        "MIXED_EVIDENCE",
        "EVIDENCE_INCOMPLETE",
    }

    gate = mcp.tools["evaluar_cierre_p3"]()
    assert gate["phase"] == "P3"
    assert gate["phase_status"] == "NOT_READY"
    assert gate["ready_for_next_phase"] is False
    assert gate["professional_emission"] is False
