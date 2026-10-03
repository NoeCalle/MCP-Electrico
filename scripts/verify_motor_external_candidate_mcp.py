import asyncio, json, os, sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
import argparse
parser=argparse.ArgumentParser()
parser.add_argument('--output',type=Path,required=True)
OUT=parser.parse_args().output.resolve()/'candidate'
def write(name, data):
    (OUT/name).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    m,p,o = [json.loads((ROOT/'examples'/f'p13_dynamic_rms_{x}.json').read_text(encoding='utf8')) for x in ('manifest','package','options')]
    s=json.loads((ROOT/'examples/p13_soft_starter_controller.json').read_text(encoding='utf8'))
    write('Inputs.json', dict(manifest=m,package=p,options=o,starter=s))
    params=StdioServerParameters(command=sys.executable,args=['-X','utf8',str(ROOT/'server.py')],cwd=str(OUT),env=dict(os.environ,PYTHONUTF8='1'))
    with (OUT/'stderr.log').open('w',encoding='utf8') as err:
        async with stdio_client(params,errlog=err) as (r,w):
            async with ClientSession(r,w) as c:
                await c.initialize()
                for name,args,file in [
                    ('ejecutar_dinamica_motores',dict(manifest=m,paquete_dinamico=p,opciones=o),'DOL.json'),
                    ('ejecutar_dinamica_arranque_suave',dict(manifest_referencia_dol=m,paquete_dinamico=p,opciones=o,arrancador=s),'SCR.json')]:
                    result=await c.call_tool(name,arguments=args)
                    if result.isError: raise RuntimeError(str(result))
                    data=result.structuredContent or json.loads(next(x.text for x in result.content if x.type=='text'))
                    write(file,data)
                    print(name,data.get('execution_status'),flush=True)
                write('Calls.json',dict(transport='MCP_STDIO',tools=['ejecutar_dinamica_motores','ejecutar_dinamica_arranque_suave']))
asyncio.run(main())

