"""Deprecated verifier redirects to migration/retirement gates.

Historical outputs remain evidence; the removed MCP physical solver cannot
produce new candidate traces. Installable MSL runs use the new verifier.
"""
from verify_modelica_motor_adapter_mcp import run
import argparse
import asyncio
from pathlib import Path

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.omc=None;args.msl=None
    asyncio.run(run(args))
