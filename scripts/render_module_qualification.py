"""Render the public qualification register without duplicating its state."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = {
    'VERIFIED_IN_SCOPE': 'Verificado en alcance',
    'IN_VERIFICATION': 'En verificación',
    'NOT_IMPLEMENTED': 'Pendiente de integración',
    'EXPLORATORY_ONLY': 'Exploratorio',
    'EDUCATIONAL_ONLY': 'Educativo',
    'DEFERRED_BY_USER': 'Diferido por el usuario',
    'RETIRED': 'Retirado',
    'EXTERNAL_RESPONSIBILITY': 'A cargo del ingeniero (fuera del software)',
}


def render(data):
    dol_closed = data['modules']['modelica_dol']['verification_status'] == 'VERIFIED_IN_SCOPE'
    lines = [
        '# Estado de cierre de módulos', '',
        f"Revisión: **{data['revision']}**. Fuente: `mcp_electrico/data/module_qualification_v1.json`.", '',
        'Documento generado con `scripts/render_module_qualification.py`; la prueba de sincronización impide publicar estados divergentes.', '',
        '## Qué se cierra', '',
        'Se cierra la integración dentro del alcance demostrado por las pruebas citadas. El respaldo del motor abierto no comprueba por sí solo las unidades, conexiones, traducción de datos y lectura de resultados del adaptador MCP.', '',
        'Los seis estados se evalúan por separado: verificación de integración, alcance soportado, preparación de datos del proyecto, criterios de diseño, conformidad normativa y aprobación del informe. Un módulo verificado puede recibir un proyecto incompleto o calcular un diseño que incumple sus criterios.', '',
        'Las nueve promociones Q1 son bancos estáticos, los cinco componentes P5 y los tres componentes P7. Su madurez pública es `VALIDATED_WITH_LIMITATIONS`, con el estado anterior como procedencia. Las ampliaciones excluidas no vuelven a abrir el alcance cerrado.', '',
        'Q2 añade el cierre DOL01–DOL03 por contraste con el ejemplo original MSL y regresión MCP. SCR conserva su calificación independiente.' if dol_closed else 'DOL conserva sus condiciones de cierre pendientes.', '',
        'La revisión, aprobación y firma del estudio corresponden al ingeniero. El software debe demostrar confiabilidad de cálculos, traducción de datos y resultados. `professional_emission=false` es un campo histórico de ausencia de aprobación automática: no impide uso, revisión o firma por el ingeniero y no exige implementar una firma digital para cerrar un módulo de cálculo. Un snapshot conserva la calificación de su fecha de captura.', '',
        '## Registro actual', '',
        '| Módulo | Motor | Estado | Alcance comprobado o solicitado |',
        '|---|---|---|---|',
    ]
    for name, item in data['modules'].items():
        clean = lambda value: str(value).replace('|', '/').replace('\n', ' ')
        lines.append(f"| `{name}` | {clean(item['engine'])} | {LABELS.get(item['verification_status'], item['verification_status'])} | {clean(item['scope'])} |")
    lines += ['', '## Condiciones finitas pendientes', '',
              ('DOL está verificado en el alcance documentado; SCR conserva `IN_VERIFICATION` con las condiciones siguientes.' if dol_closed else 'La dinámica DOL y SCR conserva `IN_VERIFICATION`: hay ejecuciones sintéticas, pero todavía falta cerrar las condiciones siguientes.') + ' La instalación de MSL no basta para aprobar un adaptador. El motor alternativo pandapower de flujo tampoco bloquea el alcance ya comprobado del motor principal OpenDSS.', '']
    for name, item in data['modules'].items():
        if not item['closure_gates']:
            continue
        lines += [f'### {name}', '']
        for gate in item['closure_gates']:
            lines.append(f"- **{gate['id']} — {gate['status']}:** {gate['acceptance']}")
        lines.append('')
    lines += ['## Condiciones cerradas con evidencia', '']
    for name, item in data['modules'].items():
        for gate in item.get('completed_closure_gates', []):
            lines.append(f"- **{name} / {gate['id']} — {gate['status']}:** {gate['acceptance']}")
    lines.append('')
    lines += ['## Evidencia y exclusiones por módulo', '']
    for name, item in data['modules'].items():
        lines += [f'### {name}', '', 'Evidencia: ' + ', '.join(f'[{Path(path).name}](../{path})' for path in item['evidence']) + '.', '']
        if item['excluded_extensions']:
            lines += ['Fuera del cierre: ' + '; '.join(item['excluded_extensions']) + '.', '']
    lines += ['## Orden del roadmap', '',
              '1. DOL cerrado en alcance: conservar su regresión contra el ejemplo original MSL y sus convenciones.' if dol_closed else '1. Cerrar DOL con referencia MSL original, convenciones de máquina y regresión reproducible del alcance admitido.',
              '2. Cerrar SCR para una máquina delta: inicialización y eventos, referencia completa y control admitido. Estrella y multimotor requieren sus pruebas propias antes de ampliarse.',
              '3. Revisar el flujo alternativo pandapower solo si una necesidad concreta justifica su alcance. Mantener OpenDSS como ruta principal ya comprobada.',
              '4. Después de esos cierres, integrar armónicos/perfiles/relés que falten usando motores existentes, sin duplicar solvers suficientes.',
              '5. Mejorar la presentación y realizar pilotos con datos reales y criterios acordados. Arc Flash continúa diferido.', '',
              'Una ficha de fabricante o la validación de un proyecto se exige al usar ese equipo; no es condición interminable para cerrar toda integración genérica. Los criterios se acuerdan por estudio y no se inventan mínimos normativos universales.', '']
    return '\n'.join(lines)


if __name__ == '__main__':
    data = json.loads((ROOT / 'mcp_electrico/data/module_qualification_v1.json').read_text(encoding='utf8'))
    (ROOT / 'docs/ESTADO_CIERRE_MODULOS.md').write_text(render(data), encoding='utf8')
