# Estado actual y próximos pasos — MCP Eléctrico

Actualizado: **17 de octubre de 2026**, calificación de transformadores Q11; registro de calificación `Q11_TRANSFORMERS_2026_10_17`.
Este documento orienta la lectura; la fuente de estados por módulo es el
[registro generado](ESTADO_CIERRE_MODULOS.md) desde
[`module_qualification_v1.json`](../mcp_electrico/data/module_qualification_v1.json).

## Aceptación integral de cálculos — 21 de octubre de 2026

P8D1 detiene la cadena ante resultados inválidos, no convergencia, excepciones,
NaN/Infinity, barras/casos MAX/MIN incompletos o revisión alterada. P5 no
consume esa ejecución y no se genera un dossier listo. Los incumplimientos de
diseño se conservan como resultados válidos con criterios fallidos.

Los dossiers incorporan `design_checks.json`, ligado al manifiesto y revisión,
y protegido por el índice de integridad. P5 exige todas las comprobaciones
solicitadas, además del tiempo de despeje. La ruta común incorpora la falla
terminal de motor Q13A, conservando su único ejecutor y su validador.

Ver [uso profesional controlado y pruebas de aceptación](USO_PROFESIONAL_CONTROLADO.md).
No amplía la calificación física ni cierra el caso industrial Brno.

## Qué está cerrado

Ampliación de protecciones: [coordinación temporal por intervalo](P5E_COORDINACION_INTERVALO.md)
con extremo global de las curvas log-log declaradas, bandas, factor de
corrientes explícito y cobertura completa o bloqueo. No acredita selectividad
integral ni completa una instalación real.

**21 módulos verificados dentro de sus alcances publicados.** La aprobación
del diseño depende de los datos y criterios de cada estudio y corresponde
al ingeniero. El MCP debe traducir correctamente esos datos, llamar al motor,
conservar evidencia y explicar errores, faltantes y resultados.

| Estudio | Ruta principal | Alcance vigente / evidencia |
|---|---|---|
| Flujo, caída, pérdidas y cargabilidad | OpenDSS | P1 y contraste externo case33bw/case69 equilibrados PQ (50/100/125%); Q11: ocho casos IEEE4 por fase y 48 variantes de transformador/taps/pérdidas; cargabilidad solo con ratings explícitos; [matriz de capacidades](MATRIZ_CAPACIDADES_ACTUALES.md) |
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

## Calificación de transformadores — Q11

Ocho casos publicados IEEE4 elevadores/reductores y equilibrados/desequilibrados,
con matrices por fase; 48 variantes controladas de siete grupos, taps HV/LV y
excitación contrastadas con AC Newton independiente. El motor operativo sigue
siendo OpenDSS. Corregidas bases nominales y proyección de corriente de vacío.
Ver [resultados, fuentes y límites](CALIFICACION_TRANSFORMADORES_Q11.md).

Las tesis investigadas quedan [clasificadas por reproducibilidad](INVESTIGACION_CASOS_SUBESTACIONES.md).
Todavía falta reproducir y revisar una instalación real completa, con cortocircuito
y protecciones sobre el mismo modelo. No se afirma una cobertura general del 90%.

## Falla terminal de motor e integral térmica — Q13A

Nueva ruta EMT MSL para un motor estrella a velocidad impuesta: corrientes
transitorias e integral i²t por fase con refinamiento y referencia independiente.
No equivale a Ith IEC ni cierra una planta completa. También se corrige el
producto frecuencia-tiempo del factor térmico del backend IEC fijado a 3.5.4.
Ver [alcance, método y pruebas](MOTOR_FAULT_THERMAL_EMT.md).

## Expediente de instalación real — Brno

Recuperados el proyecto ETAP original y tres informes SQLite de una fábrica
alimentaria existente. La auditoría encuentra ángulos de transformador distintos,
una sola ubicación de falla guardada y ajustes reales todavía no confirmados.
No se ejecutó esta fábrica mediante MCP ni se cierra la validación integral.
Ver [hallazgos y auditoría reproducible](EXPEDIENTE_INSTALACION_REAL_BRNO.md) y
[paquete concreto para cerrar el caso](PAQUETE_PARA_CERRAR_INSTALACION_REAL.md).
También quedan fuera de contrato el Ith con máquinas y la puesta a tierra
compensada si se exige reproducir íntegramente esta fábrica.

## Energía pasante total — Q12C

Nueva herramienta P5C para comparar I²t total publicado con k²S² y la
capacidad de corte del mismo dispositivo/punto. Referencia primaria ABB,
identidad y unidades explícitas, sin inventar tiempo TCC. Ver
[alcance y evidencia](ENERGIA_PASANTE_Q12C.md). La instalación real completa
y sus tiempos de despeje siguen pendientes.

## Validación de diseño real — Q12B

Siete selecciones de cables del proyecto LuPech, con corriente, duración,
k y sección publicados, contrastan la soportabilidad adiabática vía MCP.
Seis cumplen y una falla el criterio publicado; la discrepancia se conserva.
Ver [alcance y límites](VALIDACION_REAL_LUPECH_Q12B.md). La calificación de
la instalación completa y el despeje de sus protecciones siguen abiertos.

## Caso industrial — Q12A

Auditado el caso UNAM: cuatro variantes diagnósticas de la topología publicada,
con conflictos de datos y diferencias con ETAP conservados. No se acepta la
referencia como una instalación completa calificada; SC/protecciones siguen
bloqueados sin sus entradas y método correspondientes.
Ver [hallazgos y pruebas](DIAGNOSTICO_INDUSTRIAL_UNAM_Q12A.md).

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
El selector sigue siendo read-only. Hay **173 herramientas MCP** registradas.
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
