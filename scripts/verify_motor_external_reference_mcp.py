"""Call the external trace comparison through a real stdio MCP session."""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT=Path(__file__).resolve().parents[1]


async def main(output):
    params=StdioServerParameters(command=sys.executable,args=['-X','utf8',str(ROOT/'server.py')],
                                cwd=str(output),env=dict(os.environ,PYTHONUTF8='1'))
    def write(name,data):
        (output/name).write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
    with (output/'MCP-comparison-stderr.log').open('w',encoding='utf8') as err:
        async with stdio_client(params,errlog=err) as (r,w):
            async with ClientSession(r,w) as client:
                await client.initialize()
                listing=await client.list_tools()
                write('MCP-tools.json',dict(count=len(listing.tools),names=sorted(x.name for x in listing.tools)))
                response=await client.call_tool('contrastar_dinamica_con_modelica',arguments=dict(directorio_evidencia=str(output)))
                if response.isError: raise RuntimeError(str(response))
                data=response.structuredContent or json.loads(next(x.text for x in response.content if x.type=='text'))
                write('Comparacion.json',data)
                assert data['status']=='EXTERNAL_TRACE_COMPARISON_COMPLETED',data
                assert data['professional_emission'] is False
                assert data['device_validation_promoted'] is False
                write('MCP-call.json',dict(tool='contrastar_dinamica_con_modelica',transport='MCP_STDIO',
                                          candidate_calls=['ejecutar_dinamica_motores','ejecutar_dinamica_arranque_suave'],
                                          result_sha256=hashlib.sha256((output/'Comparacion.json').read_bytes()).hexdigest()))
                print(json.dumps(dict(ok=True,tools=len(listing.tools),cases=[{k:c[k] for k in ('case','mcp_reported_time_90_s','reference_time_90_s')} for c in data['cases']])))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True)
    asyncio.run(main(parser.parse_args().evidence.resolve()))
