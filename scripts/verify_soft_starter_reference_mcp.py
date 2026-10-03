"""Call the structural SCR benchmark through the real MCP protocol."""
import argparse
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


def payload(r):
    if r.isError: raise RuntimeError(str(r))
    if r.structuredContent: return r.structuredContent
    for c in r.content:
        if c.type == 'text': return json.loads(c.text)
    raise RuntimeError('No structured response')


async def main(output):
    output = output.resolve(); output.mkdir(parents=True, exist_ok=False)
    package = json.loads((ROOT/'examples/p13g_reference_comparison.json').read_text())
    # Explicit finer synthetic sweep for the published reference comparison.
    package['firing_angles_deg'] = list(range(0, 181, 5))
    def save(name, value):
        (output/name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    save('Entradas.json', package)
    params = StdioServerParameters(command=sys.executable, args=['-X', 'utf8', str(ROOT/'server.py')],
        cwd=str(output), env=dict(os.environ, PYTHONUTF8='1'))
    with (output/'MCP-stderr.log').open('w', encoding='utf-8') as err:
        async with stdio_client(params, errlog=err) as (rd, wr):
            async with ClientSession(rd, wr) as client:
                await client.initialize()
                listing = await client.list_tools()
                save('Herramientas-MCP.json', {'count':len(listing.tools), 'tools':[t.model_dump(mode='json') for t in listing.tools]})
                assert 'contrastar_arranque_suave' in {t.name for t in listing.tools}
                contract = payload(await client.call_tool('obtener_contrato_arranque_suave', arguments={}))
                save('Contrato-SCR.json', contract)
                assert contract['maturity'] == 'ANALYTICAL_SURROGATE_NOT_DEVICE_VALIDATED'
                result = payload(await client.call_tool('contrastar_arranque_suave', arguments={'paquete_comparacion':package}))
                save('Comparacion.json', result)
                assert result['status'] == 'REFERENCE_COMPARISON_COMPLETED' and result['numeric_oracle_verified']
                assert not result['agreement_same_angle'] and not result['agreement_same_fundamental']
                replay = payload(await client.call_tool('contrastar_arranque_suave', arguments={'paquete_comparacion':package}))
                assert replay == result
                invalid = deepcopy(package); invalid['tolerance_kind'] = 'NORMATIVE_REQUIREMENT'
                blocked = payload(await client.call_tool('contrastar_arranque_suave', arguments={'paquete_comparacion':invalid}))
                save('Entrada-normativa-bloqueada.json', blocked)
                assert blocked['status'] == 'BLOCKED_REFERENCE_INPUTS' and not blocked['same_angle']
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()}
    code_hashes = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        [ROOT/'mcp_electrico/soft_starter_reference.py', ROOT/'mcp_electrico/motor_soft_starting.py', ROOT/'mcp_electrico/motor_starting_tools.py']}
    save('Evidencia.json', {'transport':'stdio', 'public_tools_count':len(listing.tools),
        'tool':'contrastar_arranque_suave', 'comparison_calls':3, 'replay_match':True,
        'same_angle_points':len(result['same_angle']), 'same_fundamental_points':len(result['same_fundamental']),
        'numeric_oracle_verified':True, 'device_validation_promoted':False,
        'motor_study_performed':False, 'normative_input_blocked':True,
        'code_sha256':code_hashes, 'files_sha256':hashes})
    print(json.dumps({'ok':True, 'tools':len(listing.tools), 'output':str(output)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, required=True)
    asyncio.run(main(parser.parse_args().output))
