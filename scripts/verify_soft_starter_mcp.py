"""Exercise all five P13G public tools through a real stdio MCP client.

Only synthetic qualification inputs are used. Outputs are saved as evidence;
there is no assertion of acceptance for a real pumping station or device.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def payload(result):
    if result.isError: raise RuntimeError('MCP tool returned an error')
    if result.structuredContent: return result.structuredContent
    for item in result.content:
        if item.type == 'text': return json.loads(item.text)
    raise RuntimeError('No structured result')


async def run(directory):
    output = directory.resolve()
    output.mkdir(parents=True, exist_ok=False)
    params = StdioServerParameters(command=sys.executable, args=['-X', 'utf8', str(ROOT/'server.py')],
                                   cwd=str(output), env=dict(os.environ, PYTHONUTF8='1'))
    m, p, o = [json.loads((ROOT/'examples'/f'p13_dynamic_rms_{s}.json').read_text(encoding='utf-8')) for s in ('manifest', 'package', 'options')]
    s = json.loads((ROOT/'examples/p13_soft_starter_controller.json').read_text(encoding='utf-8'))
    arguments = dict(manifest_referencia_dol=m, paquete_dinamico=p, opciones=o, arrancador=s)
    calls = []
    with (output/'MCP-stderr.log').open('w', encoding='utf-8') as err:
        async with stdio_client(params, errlog=err) as (read, stream):
            async with ClientSession(read, stream) as client:
                await client.initialize()
                available = await client.list_tools()
                names = {t.name for t in available.tools}
                expected = {'obtener_contrato_arranque_suave', 'validar_dinamica_arranque_suave',
                            'ejecutar_dinamica_arranque_suave', 'generar_dossier_arranque_suave',
                            'verificar_integridad_dossier_arranque_suave'}
                assert expected <= names
                write(output/'Herramientas-MCP.json', dict(count=len(names), tools=sorted(names)))
                async def call(name, args, file):
                    result = payload(await client.call_tool(name, arguments=args))
                    write(output/file, result); calls.append(dict(tool=name, evidence_file=file))
                    return result
                contract = await call('obtener_contrato_arranque_suave', {}, 'Contrato.json')
                assert contract['professional_emission'] is False
                ready = await call('validar_dinamica_arranque_suave', arguments, 'Preparacion.json')
                assert ready['ready_for_execution'] and not ready['network_solve_performed']
                execution = await call('ejecutar_dinamica_arranque_suave', arguments, 'Ejecucion.json')
                assert execution['execution_status'] == 'SOFT_STARTER_STUDIES_COMPLETED', execution
                assert execution['results'][0]['current_limit_verified']
                assert execution['results'][0]['bypass_time_s'] is not None
                generated = await call('generar_dossier_arranque_suave', dict(arguments, directorio_salida=str(output/'Expediente-sintetico')), 'Dossier.json')
                assert generated['status'] == 'SOFT_STARTER_DOSSIER_READY', generated
                verified = await call('verificar_integridad_dossier_arranque_suave', dict(ruta_indice=generated['index_path']), 'Integridad.json')
                assert verified['ok'] and generated['replay_match']
                study = execution['results'][0]
                write(output/'Resumen-verificacion.json', dict(
                    public_tools_registered=len(names), public_soft_starter_tools_called=sorted(expected),
                    synthetic_case_only=True, pumping_station_M1_calculated=False,
                    execution_status=execution['execution_status'], acceleration_time_s=study['acceleration_time_s'],
                    bypass_time_s=study['bypass_time_s'], maximum_line_current_a=study['maximum_line_current_a'],
                    declared_current_limit_a=s['current_limit_a'], minimum_motor_fundamental_voltage_pu=study['minimum_voltage_pu'],
                    minimum_supply_voltage_pu=study['minimum_supply_voltage_pu'],
                    criterion_comparison_passed=study['criterion']['passed'],
                    maximum_energy_relative_error=study['verification']['maximum_energy_relative_error'],
                    parent_context_mutated=execution['parent_context_mutated'],
                    normative_compliance_demonstrated=False, device_validation_pending=True,
                    replay_match=generated['replay_match'], integrity_ok=verified['ok'],
                    workspace=generated['workspace']))
    write(output/'Llamadas-MCP.json', calls)
    print(json.dumps(dict(ok=True, directory=str(output), public_tools=len(names), calls=len(calls)), ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, required=True)
    asyncio.run(run(parser.parse_args().output))
