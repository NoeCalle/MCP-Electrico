# Estado actual y próximos pasos — MCP Eléctrico

Actualizado: **4 de octubre de 2026**, registro `Q5_TWO_SCR_2026_10_04`.
Este documento orienta la lectura; la fuente de estados por módulo es el
[registro generado](ESTADO_CIERRE_MODULOS.md) desde
[`module_qualification_v1.json`](../mcp_electrico/data/module_qualification_v1.json).

## Qué está cerrado

**18 módulos verificados dentro de sus alcances publicados.** La aprobación
del diseño depende de los datos y criterios de cada estudio y corresponde
al ingeniero. El MCP debe traducir correctamente esos datos, llamar al motor,
conservar evidencia y explicar errores, faltantes y resultados.

| Estudio | Ruta principal | Alcance vigente / evidencia |
|---|---|---|
| Flujo, caída, pérdidas y cargabilidad | OpenDSS | P1 dentro del banco radial equilibrado; [matriz de capacidades](MATRIZ_CAPACIDADES_ACTUALES.md) |
| Contingencias, transferencias y deslastre | OpenDSS | Escenarios estáticos explícitos P12; no optimización ni transferencia dinámica |
| Cortocircuito IEC 60909 | pandapower | P4-v1 3F/2F/1F-T y fichas admitidas; [alcance P4](P4_IEC60909.md) |
| Ampacidad, protección de cables y TCC | Tablas/curvas trazables + postproceso MCP | P3/P5 verificados en alcance; actuación de relés se integra por separado |
| Compensación reactiva | OpenDSS | Etapas estáticas y demanda explícitas; [evidencia](COMPENSACION_REACTIVA_OPENDSS.md) |
| Dinámica DOL | OpenModelica/MSL | Equivalente RL equilibrado y curva mecánica; bancos de una/dos máquinas; [DOL01–DOL03](MSL_DOL_VERIFICACION.md) |
| Dinámica SCR | OpenModelica/MSL | Una/dos máquinas delta, controles y bypass independientes; [Q4](MSL_SCR_REFERENCIA_ORIGINAL.md) y [Q5](MSL_SCR_DOS_MOTORES.md) |
| Expedientes e informes | MCP | P7 dentro del alcance de reconstrucción/reporte; no aprobación ni firma automática |

El MCP configura componentes existentes y procesa resultados. **La física
propia DOL/RK4 y SCR/RL está retirada**, sin fallback. No se agrega otro motor
para duplicar una ruta suficiente. Ver [arquitectura](ARQUITECTURA_INTEGRACION.md).

## Último cierre de cálculo — Q5

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

## Próximos trabajos — pendientes reales

| Orden | Integración | Qué debe demostrarse para cerrarla |
|---|---|---|
| 1 | Armónicos y resonancia con OpenDSS | Datos/espectros explícitos, ejecución MCP y contraste nativo reproducible; límites y lectura de resultados |
| 2 | Perfiles Daily/Yearly con OpenDSS | Perfiles y pasos declarados, balances, referencia nativa y resultados temporales; no es EMT |
| 3 | Actuación OCRelay con pandapower | Ajustes y actuación contrastados; tiempo de interruptor/clearing separado cuando corresponda |
| 4 | Informes y mejoras visuales | Gráficos por motor, barra/terminal separados, comparación entre casos, criterios/faltantes visibles y exportación legible |
| Continuo | Uso con datos revisados del proyecto | Modelo completo para el estudio, supuestos autorizados y expediente reproducible |

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
