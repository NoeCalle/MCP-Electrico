"""Readable overlapping print sheets of the active SVG; no new engineering."""
from html import escape
from math import ceil,isfinite
from pathlib import Path
import xml.etree.ElementTree as ET

from . import visualization,workspace_state

ET.register_namespace('', 'http://www.w3.org/2000/svg')


def export(path: str, width: float=1200, height: float=900, overlap: float=250) -> dict:
    if any(type(v) not in (int,float) or not isfinite(v) for v in (width,height,overlap)):
        raise ValueError('Dimensiones numéricas finitas requeridas.')
    if not 400<=width<=2400 or not 400<=height<=2400 or not 0<=overlap<min(width,height)/2:
        raise ValueError('Dimensiones/solape fuera del alcance de láminas.')
    target=Path(path).expanduser().resolve()
    if target.exists(): raise ValueError('La salida ya existe; elija otro nombre.')
    svg_path=target.with_name(target.stem+'_completo.svg')
    if svg_path.exists(): raise ValueError('La salida SVG ya existe; elija otro nombre.')
    target.parent.mkdir(parents=True,exist_ok=True)
    generated=visualization.generar_diagrama_unifilar(str(svg_path))
    svg=svg_path.read_text(encoding='utf-8')
    original=ET.fromstring(svg)
    x,y,w,h=map(float,original.attrib['viewBox'].split())
    cols=max(1,ceil((w-overlap)/(width-overlap))); rows=max(1,ceil((h-overlap)/(height-overlap)))
    if cols*rows>200:
        svg_path.unlink()
        raise ValueError('La red requiere más de 200 láminas con estas dimensiones.')
    state=workspace_state.status(); sheets=[]
    for row in range(rows):
        for col in range(cols):
            startx=x+col*(width-overlap);starty=y+row*(height-overlap)
            tile=ET.fromstring(svg)
            tile.set('viewBox',f'{startx} {starty} {width} {height}')
            tile.set('width',str(width));tile.set('height',str(height))
            rendered=ET.tostring(tile,encoding='unicode')
            number=row*cols+col+1
            sheets.append(f'<section class="sheet"><h2>Lámina {number} / {rows*cols} · Fila {row+1}, columna {col+1}</h2><p>Revisión {state["model_revision"]} · Solape {overlap:g} unidades SVG · Consulte el SVG completo para continuidad.</p>{rendered}</section>')
    html='''<!doctype html><html lang="es"><meta charset="utf-8"><title>Láminas del unifilar</title><style>body{margin:0;font:12px system-ui;background:#eaf0f5;color:#20384d}.sheet{max-width:1200px;margin:24px auto;padding:16px;background:white;box-shadow:0 2px 14px #20384d22}svg{width:100%;height:auto}h2{margin:0;font-size:16px}@page{size:A3 landscape;margin:12mm}@media print{body{background:white}.sheet{margin:0;padding:0;max-width:none;box-shadow:none;break-after:page}.sheet:last-child{break-after:auto}svg{width:100%;max-height:245mm}}</style>'''+''.join(sheets)+'</html>'
    target.write_text(html,encoding='utf-8')
    return {'status':'VISUAL_SHEETS_READY','html_path':str(target),'svg_path':str(svg_path),
            'sheet_count':rows*cols,'columns':cols,'rows':rows,'model_revision':state['model_revision'],
            'results_current':state['results_current'],'browser_engineering_calculation':False,'professional_emission':False}


def register(mcp):
    @mcp.tool()
    def exportar_laminas_unifilar(ruta_html: str, ancho_svg: float=1200, alto_svg: float=900, solape_svg: float=250) -> dict:
        """Exporta el unifilar activo en láminas A3 con solape y numeración, sin resolver."""
        return export(ruta_html,ancho_svg,alto_svg,solape_svg)
