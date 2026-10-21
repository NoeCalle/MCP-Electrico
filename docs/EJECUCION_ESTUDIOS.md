# Ejecución de estudios por su motor asignado

Actualizado: 17 de octubre de 2026. Orquestación sobre los adaptadores existentes;
no amplía su calificación física ni normativa.

`ejecutar_estudio` recibe un identificador de estudio y sus parámetros explícitos,
elige una ruta de la tabla y llama **una sola vez** a su ejecutor público.
No compara motores, completa datos ni cambia de motor si la ejecución falla.
ChatGPT interpreta la petición en lenguaje natural y prepara esos argumentos;
el servidor no interpreta texto libre como una secuencia de maniobras.

| Identificador / alias | Motor o capa | Ejecutor público |
|---|---|---|
| `motor_terminal_fault_emt` / `falla_terminal_motor` | OpenModelica/MSL | `ejecutar_falla_terminal_motor_modelica`, un motor estrella a velocidad impuesta |
| `power_flow` / `flujo` | OpenDSS | `ejecutar_flujo_potencia` |
| `voltage_drop` / `caida_tension` | OpenDSS + postproceso | `analizar_caida_tension` |
| `operating_scenarios` / `N-1` / `contingencias` | OpenDSS | `ejecutar_escenarios_operativos` |
| `iec60909` | pandapower | Herramienta 3F, 2F o 1F-T según `tipo_falla` |
| `ampacity` / `ampacidad` | MCP, tablas trazables | `evaluar_ampacidad` |
| `protection_coordination` | MCP, curvas y corrientes declaradas | `evaluar_coordinacion_temporal_p5e` |
| `protection_coordination_range` / `coordinacion_intervalo` | MCP, curvas y factor de corrientes declarados | `evaluar_coordinacion_intervalo_p5e` |
| `reactive_compensation` | OpenDSS | `ejecutar_compensacion_reactiva` |
| `harmonics` / `armonicos` | OpenDSS | `ejecutar_armonicos` |
| `time_series` / `series_temporales` | OpenDSS | `ejecutar_series_temporales` |
| `motor_dynamics_dol` / `dinamica_arranque_directo` | OpenModelica/MSL | `ejecutar_dinamica_modelica` |
| `motor_dynamics_simultaneous` / `dinamica_simultanea` | OpenModelica/MSL | `ejecutar_dinamica_modelica`, al menos dos DOL |
| `motor_dynamics_soft_starter_scr` / `dinamica_scr` | OpenModelica/MSL | `ejecutar_dinamica_modelica`, una/dos SCR |

La coordinación P5E evalúa margen temporal **puntual** a corrientes explícitas;
no vuelve a calcular cortocircuitos ni declara selectividad integral. La matriz
histórica identifica la cadena MCP+pandapower; esta llamada usa las corrientes
ya declaradas. La ampacidad conserva los faltantes de Ib/In/Iz y sus fuentes.

La nueva ruta de intervalo evalúa el peor margen continuo de curvas log-log
declaradas con factor de corrientes constante, sin huecos ni extrapolación.
Su alcance y sus comprobaciones son independientes de la ruta puntual y no
acreditan selectividad integral. Ver [contrato y banco](P5E_COORDINACION_INTERVALO.md).

## Uso

Primero consultar `obtener_contrato_ejecucion_estudios`: devuelve los esquemas
de parámetros de los ejecutores registrados, sin mantener una copia manual.
Los nombres y campos son los mismos de las herramientas específicas.

Con un circuito activo:

```json
{"estudio": "flujo", "parametros": {}}
```

Con un paquete armónico completo según `obtener_contrato_armonicos`, enviarlo
como `parametros.paquete_estudio` y declarar `parametros.directorio_salida`.
Se conservan las entradas, resultados, informe e integridad del ejecutor Q6.
El mismo patrón se usa para compensación, series, relés y Modelica.

IEC exige `tipo_falla`: `three_phase`, `two_phase` o `single_phase_ground`.
`cortocircuito` solo se enruta si además se declara `norma: "IEC 60909"`;
no se convierte una petición genérica en FaultStudy exploratorio. Los parámetros
incluyen `bus_falla` y los datos del ejecutor correspondiente. Para 3F también
se mantiene `revision_modelo`: primero consultar
`evaluar_preparacion_cortocircuito_3ph`, revisar faltantes/supuestos/exclusiones
y proporcionar la revisión explícita vigente. El despacho no la fabrica.
2F-T sigue excluida de esta entrada común.

`N-1` recibe `manifest` y `paquete_escenarios`: **P12 reconstruye y restaura
la base declarada en ese manifest**, que pasa a ser el circuito activo. No
restaura un circuito previo distinto. Ejecuta las acciones declaradas; no
elige automáticamente contingencias, fuentes ni cargas a desconectar.

Modelica recibe exclusivamente su paquete de equivalente RL. El despacho no
traduce el unifilar ni permite pedir SCR y ejecutar un paquete DOL. Conserva
el gate de runtime, admisión, refinamiento e informe Q9. No habilita VFD,
mezclas DOL/SCR, más de dos SCR ni SCR estrella.

## Lectura de la respuesta

- `selected_engine` y `execution_tool` identifican la ruta.
- `executor_invoked=false` indica bloqueo previo a invocar el ejecutor.
- `EXECUTOR_RETURNED` significa que el ejecutor devolvió un objeto, **no** que
  el estudio convergió, cumplió criterios o quedó aprobado. Leer `result`, que
  conserva el objeto original, incluidos bloqueos, resultados inválidos y faltantes.
- `EXECUTOR_ERROR` o `EXECUTOR_RESPONSE_UNAVAILABLE` no provocan reintentos.
  Revisar el problema y los artefactos antes de una nueva petición.

Se rechazan parámetros desconocidos, campos requeridos ausentes, tipos
incompatibles y números no finitos antes de invocar una herramienta. La
validación física y de datos sigue perteneciendo al adaptador.

`seleccionar_motor_estudio` y `evaluar_preparacion_estudio` siguen siendo
read-only: `automatic_dispatch=false` describe esas consultas, no la ausencia
de la nueva entrada explícita. `obtener_capacidades_motores.execution_dispatch`
expone las rutas habilitadas. No hay ejecución espontánea o en segundo plano.
Las herramientas específicas existentes continúan disponibles.

## Verificación

- `tests/test_study_dispatch.py`: rutas, invocación única, errores sin fallback,
  contrato SDK, integraciones nativas, efectos del modelo y gates conservados.
- `scripts/verify_study_dispatch_mcp.py`: conexión MCP stdio real, **26 llamadas**,
  **168 herramientas** registradas, flujo/caída contrastados con las herramientas
  públicas, cuatro adaptadores con artefactos, IEC 3F revisado y escenarios P12.
- [Evidencia MCP](evidence/study_dispatch_mcp.json): fuentes y hashes.
- CI Linux/Windows en `.github/workflows/study-dispatch.yml`.

Los datos de prueba son sintéticos. Esta verificación comprueba orquestación;
no es una nueva simulación física Modelica ni un estudio de proyecto aprobado.
