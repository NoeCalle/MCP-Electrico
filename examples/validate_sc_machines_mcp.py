"""Validate synthetic machine benchmarks via actual public MCP stdio tools.

No engineering assumptions for a user project are authorized by this example.
"""
import argparse
import asyncio
import json
import math
import os
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


def impedance(z, rx):
    x = z / math.sqrt(1+rx**2)
    return complex(rx*x, x)


async def run(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    calls, checks = [], []
    params = StdioServerParameters(command=sys.executable, args=["-X", "utf8", str(ROOT/"server.py")],
                                   cwd=str(out), env=dict(os.environ, PYTHONUTF8="1"))
    with (out/"server-stderr.log").open("w", encoding="utf-8") as errlog:
      async with stdio_client(params, errlog=errlog) as (read, write):
       async with ClientSession(read, write) as client:
        await client.initialize()
        catalog = await client.list_tools()
        names = {t.name for t in catalog.tools}
        required = {"definir_motor_cortocircuito_3ph", "definir_generador_cortocircuito_3ph",
                    "clasificar_carga_cortocircuito_3ph", "obtener_fichas_maquinas_cortocircuito_3ph",
                    "eliminar_ficha_maquina_cortocircuito_3ph"}
        assert required <= names
        async def call(name, **args):
            r = await client.call_tool(name, arguments=args)
            v = r.structuredContent
            if v is None:
                raw = next(b.text for b in r.content if b.type == "text")
                try:
                    v = json.loads(raw)
                except json.JSONDecodeError:
                    v = raw
            calls.append({"tool":name,"arguments":args,"response":v,"is_error":r.isError})
            assert not r.isError, (name, v)
            return v

        for configuration in ("UTILITY_MOTOR", "GENERATOR_UNIT_MOTOR"):
            await call("crear_circuito", nombre="synthetic_sc_mcp", kv_base=13.8, frecuencia=60.)
            await call("configurar_workspace", ruta_salida=str(out/"workspace.html"), auto_regenerar=False)
            await call("agregar_carga", nombre="motor", bus="sourcebus", kw=500., kvar=200., kv=13.8, fases=3)
            await call("definir_motor_cortocircuito_3ph", elemento_carga="Load.motor", pn_mecanica_mw=.8,
                       vn_kv=13.8, eficiencia_nominal_pct=95., fp_nominal=.9,
                       corriente_rotor_bloqueado_pu=6., relacion_r_x=.1,
                       referencia="Synthetic independent module benchmark: explicit illustrative motor sheet")
            bus, expected = "sourcebus", {}
            if configuration == "UTILITY_MOTOR":
                await call("definir_red_equivalente", kv_ll=13.8, scc_max_mva=500., x_r_max=10.,
                           scc_min_mva=250., x_r_min=5., fuente_referencia="Synthetic source benchmark")
                zm = impedance(13.8**2/(.8/.95/.9*6), .1)
                ze = impedance(1.1*13.8**2/500, .1)
                expected = {"max":1.1*13.8/math.sqrt(3)*abs(1/ze+1/zm), "min":250/math.sqrt(3)/13.8}
            else:
                await call("agregar_transformador_profesional", nombre="tgen", bus_hv="hv", bus_lv="sourcebus",
                           kva=40000., kv_hv=138., kv_lv=13.8, uk_percent=10., grupo_vectorial="Yy0", x_r=10.,
                           no_load_loss_kw=40., i0_percent=.5, fuente_referencia="Synthetic unit benchmark")
                await call("definir_generador_cortocircuito_3ph", elemento="Vsource.source", sn_mva=37.5,
                           vn_kv=13.8, xdss_pu=.2, rdss_ohm=.03, fp_nominal=.8, pg_percent=0.,
                           referencia="Synthetic generator benchmark", transformador_unidad="Transformer.tgen",
                           oltc=False, pt_percent=0.)
                bus = "hv"
                zt = impedance(.1*138**2/40., .1)
                zg = complex(.03, .2*13.8**2/37.5) * 100
                zm = impedance(13.8**2/(.8/.95/.9*6), .1) * 100
                ks = 1.1/(1+.2*.6)
                expected = {"max":1.1*138/math.sqrt(3)/abs(ks*zt + 1/(1/(ks*zg)+1/zm)),
                            "min":138/math.sqrt(3)/abs(ks*(zt+zg))}
            inv = await call("obtener_fichas_maquinas_cortocircuito_3ph")
            assert not inv["issues"], inv
            p = await call("evaluar_preparacion_cortocircuito_3ph", bus_falla=bus)
            assert p["numerical_ready"], p
            blocked = await call("ejecutar_cortocircuito_iec60909_3ph", bus_falla=bus)
            assert blocked["execution_status"] == "BLOQUEADO_ANTES_DEL_CALCULO"
            r = await call("ejecutar_cortocircuito_iec60909_3ph", bus_falla=bus, revision_modelo={
                "model_sha256":p["model_sha256"], "uso_previsto":p["supported_scope"],
                "calidad_datos":"SUPUESTOS_APROBADOS",
                "referencia_revision":"Synthetic module validation only; not approval of a real project",
                "supuestos_aprobados":["All inputs are declared numerical test fixtures, not manufacturer data."],
                "exclusiones_revisadas":[i["id"] for i in p["items_to_review"]]})
            assert r["ok"], r
            for case, value in expected.items():
                observed = r["scenarios"][case]["results"]["ikss_ka"]
                error = abs(observed/value - 1)
                checks.append({"configuration":configuration,"case":case,"expected_ka":value,
                               "observed_ka":observed,"relative_error":error,"passed":error<2e-5})
                assert error < 2e-5, checks[-1]
            print(configuration+": MAX/MIN independent impedance benchmark PASS", flush=True)
        await call("eliminar_ficha_maquina_cortocircuito_3ph", elemento="Load.motor")
        p = await call("evaluar_preparacion_cortocircuito_3ph", bus_falla="hv")
        assert not p["numerical_ready"]
    (out/"calls.json").write_text(json.dumps(calls, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    summary = {"schema":"MCP_SC3_MACHINE_STDIO_VALIDATION_V1", "server":str(ROOT/"server.py"),
               "public_tool_count":len(names),"public_tool_calls":len(calls), "benchmarks":checks,
               "passed":all(c["passed"] for c in checks), "synthetic_only":True,
               "new_user_project_assumptions_approved":False, "professional_emission":False}
    (out/"validation.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    asyncio.run(run(Path(parser.parse_args().output_dir).resolve()))
