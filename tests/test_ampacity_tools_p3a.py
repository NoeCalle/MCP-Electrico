from mcp_electrico import ampacity_tools


class FakeMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn
        return decorator


def test_p3a_tools_quedan_registradas_sin_duplicar_motor_numerico():
    mcp = FakeMCP()
    ampacity_tools.register(mcp, on_study=lambda *_args, **_kwargs: None)

    assert {
        "listar_referencias_ampacidad",
        "listar_perfiles_normativos_ampacidad",
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
