"""Exercise continuous curve envelopes over real MCP stdio with synthetic data."""
import argparse
import asyncio
from datetime import timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


def points(currents, times):
    return [{"current_a": i, "time_s": t} for i, t in zip(currents, times)]


async def verify(output):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    calls = []
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "server.py")],
                                   cwd=str(output), env=dict(os.environ, PYTHONUTF8="1"))
    with (output / "MCP-stderr.log").open("w", encoding="utf8") as stderr:
        async with stdio_client(params, errlog=stderr) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=60)) as client:
                await client.initialize()

                async def call(name, arguments):
                    response = await client.call_tool(name, arguments)
                    assert not response.isError, response
                    result = response.structuredContent
                    if result is None:
                        raw = next(c.text for c in response.content if c.type == "text")
                        try:
                            result = json.loads(raw)
                        except ValueError:
                            result = raw
                    entry = {"tool": name, "arguments": arguments, "result": result}
                    calls.append(entry)
                    (output / f"call-{len(calls):03d}.json").write_text(
                        json.dumps(entry, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf8")
                    return result

                await call("crear_circuito", {"nombre": "synthetic_range_not_field_installation", "kv_base": .48})
                for name, b1, b2 in (("f1", "sourcebus", "b1"), ("f2", "b1", "b2")):
                    await call("agregar_linea", {"nombre": name, "bus1": b1, "bus2": b2,
                                               "longitud_km": .05, "r1_ohm_km": .2, "x1_ohm_km": .08})

                async def bind(name, element, segments, semantics="TOTAL_CLEARING_TIME"):
                    await call("definir_dispositivo_proteccion_p5a", {
                        "nombre": name, "tipo": "circuit_breaker", "elemento_protegido": element,
                        "in_a": 100, "ue_kv": .48, "norma_referencia": "SYNTHETIC_TEST_NOT_COMPLIANCE",
                        "fuente_referencia": "SYNTHETIC_TEST_NOT_MANUFACTURER"})
                    await call("vincular_curva_proteccion_p5a", {
                        "dispositivo": name, "curva_id": name, "tipo_curva": "TEST_CURVE",
                        "fuente_referencia": "SYNTHETIC_ANALYTICAL_CURVE"})
                    await call("registrar_dataset_curva_tcc_p5b", {
                        "dataset_id": name, "curve_id": name, "shape": "SINGLE",
                        "time_semantics": semantics, "segments": segments,
                        "source_type": "TEST_DATA", "source_reference": "SYNTHETIC_ANALYTICAL_CURVE"})
                    await call("vincular_dataset_curva_tcc_p5b", {"dispositivo": name, "dataset_id": name})

                async def evaluate(down, up, low, high, margin, ratio=1):
                    result = await call("ejecutar_estudio", {"estudio": "coordinacion_intervalo", "parametros": {
                        "dispositivo_downstream": down, "dispositivo_upstream": up,
                        "corriente_minima_downstream_a": low, "corriente_maxima_downstream_a": high,
                        "factor_corriente_upstream": ratio, "margen_minimo_s": margin,
                        "fuente_relacion": "SYNTHETIC_EXPLICIT_PAIR", "fuente_corrientes": "SYNTHETIC_RANGE_AND_RATIO"}})
                    assert result["execution_tool"] == "evaluar_coordinacion_intervalo_p5e", result
                    assert result["selected_engine"] == "mcp" and not result["fallback"]
                    return result["result"]

                segment = lambda p: [{"id": "s", "points": p}]
                await bind("down", "Line.f2", segment(points([100, 10000], [1, 1])))
                await bind("up_pass", "Line.f1", segment(points([50, 5000], [3, 3])))
                good = await evaluate("down", "up_pass", 100, 10000, 1, .5)
                assert good["status"] == "PASS" and good["full_requested_range_evaluated"], good
                await bind("up_valley", "Line.f1", segment(points([100, 1000, 10000], [3, .5, 3])))
                for current in (100, 10000):
                    endpoint = await call("evaluar_coordinacion_temporal_p5e", {
                        "dispositivo_downstream": "down", "dispositivo_upstream": "up_valley",
                        "corriente_downstream_a": current, "corriente_upstream_a": current,
                        "margen_minimo_s": 1, "fuente_relacion": "SYNTHETIC_PAIR",
                        "fuente_corrientes": "SYNTHETIC_ENDPOINT"})
                    assert endpoint["status"] == "PASS", endpoint
                hidden = await evaluate("down", "up_valley", 100, 10000, 1)
                assert hidden["status"] == "FAIL" and hidden["resultados_validos"], hidden
                assert abs(hidden["worst_case"]["conservative_margin_s"] + .5) < 1e-10
                await bind("up_gap", "Line.f1", [
                    {"id": "a", "points": points([100, 200], [3, 3])},
                    {"id": "b", "points": points([2000, 10000], [3, 3])}])
                gap = await evaluate("down", "up_gap", 100, 10000, 1)
                assert gap["status"] == "COORDINATION_RANGE_NOT_READY" and not gap["resultados_validos"]
                await bind("up_trip", "Line.f1", segment(points([100, 10000], [3, 3])), "TRIP_TIME")
                trip = await evaluate("down", "up_trip", 100, 10000, 1)
                assert trip["status"] == "COORDINATION_RANGE_NOT_READY"
                assert trip["issues"][0]["reason"] == "TIME_SEMANTICS_NOT_CLEARING_READY"
                await bind("down_power", "Line.f2", segment(points([100, 400], [1, .25])))
                await bind("up_power", "Line.f1", segment(points([100, 400], [1, .0625])))
                stationary = await evaluate("down_power", "up_power", 100, 400, 0)
                assert stationary["worst_case"]["kind"] == "INTERIOR_STATIONARY_POINT"
                assert abs(stationary["worst_case"]["downstream_current_a"] - 200) < 1e-8
                for result in (good, hidden, gap, trip, stationary):
                    assert result["claims"]["selectivity"] == "NOT_EVALUATED"
                    assert not result["professional_emission"]

    summary = {"schema": "MCP_ELECTRICO_P5E_RANGE_ACCEPTANCE_V1", "passed": True,
               "reference": "SYNTHETIC_ANALYTICAL_NOT_FIELD_OR_MANUFACTURER",
               "call_count": len(calls), "scenarios": {
                   "explicit_ratio_pass": good["status"], "hidden_knot_failure": hidden["status"],
                   "gap_blocked": gap["status"], "trip_time_blocked": trip["status"],
                   "interior_stationary_point": stationary["worst_case"]},
               "installation_validation_closed": False,
               "sha256": {p.name: sha256(p.read_bytes()).hexdigest() for p in sorted(output.glob("call-*.json"))},
               "sources_sha256": {p: sha256((ROOT / p).read_bytes()).hexdigest() for p in (
                   "mcp_electrico/protection_coordination_range.py", "mcp_electrico/protection_coordination_tools.py",
                   "mcp_electrico/engine_selection.py", "mcp_electrico/study_dispatch.py")}}
    (output / "Summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf8")
    print(json.dumps({"passed": True, "call_count": len(calls), "output": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(asyncio.wait_for(verify(parser.parse_args().output), timeout=300))
