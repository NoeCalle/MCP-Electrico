# Estado actual y próximos pasos — MCP Eléctrico

Actualizado: **17 de octubre de 2026**, ejecución por ruta y presentación Q9; registro de calificación `Q10_EXTERNAL_FEEDERS_2026_10_17`.
Este documento orienta la lectura; la fuente de estados por módulo es el
[registro generado](ESTADO_CIERRE_MODULOS.md) desde
[`module_qualification_v1.json`](../mcp_electrico/data/module_qualification_v1.json).

## Qué está cerrado

**21 módulos verificados dentro de sus alcances publicados.** La aprobación
del diseño depende de los datos y criterios de cada estudio y corresponde
al ingeniero. El MCP debe traducir correctamente esos datos, llamar al motor,
conservar evidencia y explicar errores, faltantes y resultados.

| Estudio | Ruta principal | Alcance vigente / evidencia |
|---|---|---|
| Flujo, caída, pérdidas y cargabilidad | OpenDSS | P1 y contraste externo case33bw/case69 equilibrados PQ (50/100/125%); cargabilidad solo con ratings explícitos; [matriz de capacidades](MATRIZ_CAPACIDADES_ACTUALES.md) |
| Contingencias, transferencias y deslastre | OpenDSS | Escenarios estáticos explícitos P12; no optimización ni transferencia dinámica |
| Cortocircuito IEC 60909 | pandapower | P4-v1 3F/2F/1F-T y fichas admitidas; [alcance P4](P4_IEC60909.md) |
| Ampacidad, protección de cables y TCC | Tablas/curvas trazables + postproceso MCP | P3/P5 verificados en alcance; Q8 OCRelay tiene su contrato independiente |
| Compensación reactiva | OpenDSS | Etapas estáticas y demanda explícitas; [evidencia](COMPENSACION_REACTIVA_OPENDSS.md) |
| Dinámica DOL | OpenModelica/MSL | Equivalente RL equilibrado y curva mecánica; bancos de una/dos máquinas; [DOL01–DOL03](MSL_DOL_VERIFICACION.md) |
| Dinámica SCR | OpenModelica/MSL | Una/dos máquinas delta, controles y bypass independientes; [Q4](MSL_SCR_REFERENCIA_ORIGINAL.md) y [Q5](MSL_SCR_DOS_MOTORES.md) |
| Armónicos y barrido de impedancia | OpenDSS | Q6: espectros no triplén y barrido positivo con amortiguamiento explícito; [evidencia y límites](ARMONICOS_OPENDSS.md) |
| Perfiles Daily/Yearly | OpenDSS | Q7: perfiles P/Q explícitos, energía del periodo y criterios por intervalo; [evidencia y límites](SERIES_TEMPORALES_OPENDSS.md) |
| Actuación de relés | pandapower OCRelay | Q8: DTOC/IDMT/IDTOC y corrientes constantes explícitas; [límites y evidencia](ACTUACION_RELES_PANDAPOWER.md) |
| Expedientes e informes | MCP | P7 dentro del alcance de reconstrucción/reporte; no aprobación ni firma automática |

El MCP configura componentes existentes y procesa resultados. **La física
propia DOL/RK4 y SCR/RL está retirada**, sin fallback. No se agrega otro motor
para duplicar una ruta suficiente. Ver [arquitectura](ARQUITECTURA_INTEGRACION.md).

## Calificación externa — Q10

Dos redes publicadas (33/69 barras), seis niveles/casos de carga contrastados
contra PYPOWER AC Newton como referencia de validación; ejecución operativa
OpenDSS mediante MCP. Se verifican 100 aperturas radiales, pérdida de servicio
y restauración. Las fronteras PF y los rangos PQ se declaran explícitamente;
no se inventan SCC, ratings ni paquetes de otros estudios.
Ver [resultados, fuentes y límites](CALIFICACION_ALIMENTADORES_EXTERNOS.md).

## Último cierre de presentación — Q9

Informe MSL por motor, comparación de casos guardados, curvas de barra/terminal
separadas, criterios y faltantes visibles, CSV/SVG/HTML e impresión legible.
No cambia los alcances numéricos ni la calificación histórica de los estudios.
Ver [uso y evidencia Q9](INFORMES_MOTORES_Q9.md).

## Ejecución por motor asignado

`ejecutar_estudio` conecta la tabla con los ejecutores públicos: flujo/caída,
escenarios P12, IEC 3F/2F/1F-T, ampacidad, coordinación temporal puntual,
compensación, armónicos, series y paquetes Modelica. Conserva sus gates,
resultados, efectos de modelo y reportes; no ejecuta dos motores ni hace fallback.
El selector sigue siendo read-only. Hay **168 herramientas MCP** registradas.
Ver [contrato, parámetros y evidencia](EJECUCION_ESTUDIOS.md).

## Último cierre de cálculo — Q8

Actuación OCRelay DTOC/IDMT/IDTOC verificada con 61 pruebas y 79 llamadas MCP
(432 puntos de corriente). Ajustes y corrientes RMS primarias constantes explícitos;
tiempo del relé e interruptor separados. No calcula una secuencia de aperturas ni
acredita selectividad integral. Ver [alcance Q8](ACTUACION_RELES_PANDAPOWER.md).

## Cierre anterior — Q7

Perfiles Daily/Yearly verificados con 16 combinaciones PQ/Z independientes,
referencia nativa, prueba de 8.760 h y 39 llamadas MCP. Cada carga declara P y Q;
no se extrapolan datos a un año ni se publica energía de una serie parcial.
El circuito padre permanece intacto. Ver [alcance Q7](SERIES_TEMPORALES_OPENDSS.md).

## Cierre anterior — Q6

Armónicos y barrido de impedancia están verificados en el alcance equilibrado
publicado: 24 combinaciones RL/C independientes, contraste nativo, ejemplo con
transformador y 54 llamadas MCP. Se conserva el circuito padre y se archivan
entradas, fasores, informe y hashes. Los picos son máximos muestreados que
requieren refinamiento. Ver [alcance Q6](ARMONICOS_OPENDSS.md).

## Cierre anterior — Q5

La ampliación de dos SCR se integró en
[#163](https://github.com/NoeCalle/MCP-Electrico/pull/163), commit
`c49ceec6d7044107c42091899a2e737d6915022c`. Su evidencia registra:

- **7 estudios completos**: seis de dos motores y un control de una máquina.
- **18 llamadas MCP**, 14 trazas nominal/refinada y 26 comprobaciones por máquina.
- Arranques simultáneos, solapados y después del bypass de M1; 50/60 Hz;
  inercias, amortiguamientos y curvas de carga diferentes.
- Contraste original MSL, equivalencia Z/2Z, KVL con corrientes de ambas ramas,
  balances mecánicos individuales y espera/enclavamiento del bypass.
- Suite local **968 aprobadas, una omitida**; **77 comprobaciones CI aprobadas**;
  seis llamadas MCP posteriores a la instalación.

La CI comprueba contratos, lectores y regresiones; el banco físico usa el
runtime local fijado por hashes. Los casos son sintéticos de integración y
**no son un estudio aprobado de las bombas del proyecto**. Los intentos fallidos
se conservan y no se promueven a resultados verificados.

Cada estudio nuevo exige datos explícitos, criterios acordados y refinamiento.
La admisión DOL permite hasta ocho máquinas, pero los bancos publicados
contrastan una/dos. SCR admite una/dos máquinas delta; más de dos SCR, mezclas
DOL/SCR y SCR estrella están bloqueados. El controlador MSL es genérico;
fabricante y traducción automática del unifilar completo no están calificados.

## Trabajos priorizados y pendientes vigentes

| Orden | Integración | Qué debe demostrarse para cerrarla |
|---|---|---|
| Cerrado | Tabla → ejecutor por estudio | Entrada común, una ruta por llamada, contratos y gates conservados; [uso y evidencia](EJECUCION_ESTUDIOS.md) |
| Cerrado Q9 | Informes de motores MSL | Gráficos por motor, barra/terminal separados, comparación, criterios/faltantes, CSV/SVG/HTML e impresión; [alcance](INFORMES_MOTORES_Q9.md) |
| Continuo | Uso con datos revisados del proyecto | Modelo completo para el estudio, supuestos autorizados y expediente reproducible |

Las integraciones priorizadas Q6-Q8 y la presentación de motores Q9 están cerradas
en sus alcances. Las mejoras de otros informes se priorizan por una necesidad
concreta del estudio; no se declara terminada toda posible ampliación visual.

El flujo alternativo pandapower sigue **en verificación** (PPF01–PPF02).
OpenDSS continúa como ruta principal; completar una ruta duplicada solo se
prioriza si el proyecto demuestra que la necesita. Las ampliaciones de datos,
normativa y fenómenos están en [validaciones pendientes](VALIDACIONES_PENDIENTES.md)
y en las exclusiones de cada módulo. **Arc Flash IEEE 1584 permanece diferido**.

## Instalación, selección y lectura de documentos

La instalación es local en esta PC. Actualizar archivos no recarga un servidor
Python ya abierto: reconectar `mcp-electrico` o reiniciar el cliente permite
cargar el código nuevo. Una sesión MCP fresca confirma la versión; la presencia
del servidor en ajustes no demuestra por sí sola cuál código está en memoria.

El selector genérico conserva `implemented=false` para la dinámica del unifilar
completo. Eso coexiste con `VERIFIED_SCOPED_ADAPTER_ONLY`: el paquete Modelica
tiene su propio validador y ejecución. Ver [selección de motor](ENGINE_SELECTION.md).

Los snapshots, expedientes y documentos de hitos anteriores conservan su fecha
y estado original. Los documentos P13F/P13G de física propia son históricos.
`professional_emission=false` significa ausencia de aprobación automática;
no impide al ingeniero revisar, usar, aprobar y firmar un estudio.

- [Matriz detallada](MATRIZ_CAPACIDADES_ACTUALES.md).
- [Roadmap maestro](ROADMAP_PROFESIONAL.md).
- [Roadmap visual](ROADMAP_VISUAL.md).
- [Migración y necesidades industriales](MIGRACION_MODELOS_ABIERTOS.md).
- [Cierre de módulos y evidencia](ESTADO_CIERRE_MODULOS.md).
