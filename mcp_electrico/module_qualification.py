"""Authoritative scoped integration qualifications; no solver or project approval."""
from copy import deepcopy
import json
from pathlib import Path

PATH=Path(__file__).resolve().parent/'data/module_qualification_v1.json'
VERIFIED='VERIFIED_IN_SCOPE'


def catalogue():
    return json.loads(PATH.read_text(encoding='utf8'))


def get(name):
    data=catalogue()
    return {'revision':data['revision'],**deepcopy(data['modules'][name])}


def register(mcp):
    @mcp.tool()
    def obtener_estado_cierre_modulos() -> dict:
        """Estado por alcance, evidencia y condiciones de cierre; separa datos, diseño y aprobación."""
        return catalogue()
