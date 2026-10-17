# Estado de cierre de módulos

Revisión: **Q11_TRANSFORMERS_2026_10_17**. Fuente: `mcp_electrico/data/module_qualification_v1.json`.

Documento generado con `scripts/render_module_qualification.py`; la prueba de sincronización impide publicar estados divergentes.

**Resumen:** 21 módulos verificados en alcance; 1 en verificación; 0 pendientes de integración. Ver [estado actual y prioridades](ESTADO_ACTUAL.md).

## Qué se cierra

Se cierra la integración dentro del alcance demostrado por las pruebas citadas. El respaldo del motor abierto no comprueba por sí solo las unidades, conexiones, traducción de datos y lectura de resultados del adaptador MCP.

Los seis estados se evalúan por separado: verificación de integración, alcance soportado, preparación de datos del proyecto, criterios de diseño, conformidad normativa y aprobación del informe. Un módulo verificado puede recibir un proyecto incompleto o calcular un diseño que incumple sus criterios.

Las nueve promociones Q1 son bancos estáticos, los cinco componentes P5 y los tres componentes P7. Su madurez pública es `VALIDATED_WITH_LIMITATIONS`, con el estado anterior como procedencia. Las ampliaciones excluidas no vuelven a abrir el alcance cerrado.

Q2 añade el cierre DOL01–DOL03 por contraste con el ejemplo original MSL y regresión MCP. SCR conserva su calificación independiente.

La revisión, aprobación y firma del estudio corresponden al ingeniero. El software debe demostrar confiabilidad de cálculos, traducción de datos y resultados. `professional_emission=false` es un campo histórico de ausencia de aprobación automática: no impide uso, revisión o firma por el ingeniero y no exige implementar una firma digital para cerrar un módulo de cálculo. Un snapshot conserva la calificación de su fecha de captura.

## Registro actual

| Módulo | Motor | Estado | Alcance comprobado o solicitado |
|---|---|---|---|
| `power_flow` | OpenDSS | Verificado en alcance | Radial trifásico equilibrado PQ: dos barras y case33bw/case69 publicados, 50/100/125% de carga, frontera slack PF explícita; IEEE4 de cuatro nodos (ocho casos por fase) y 48 variantes equilibradas de transformador/taps/excitacion |
| `voltage_drop` | OpenDSS + postproceso | Verificado en alcance | Caída por Line: alcance P1 y ramas de case33bw/case69 equilibrados, 50/100/125% de carga |
| `conductor_library` | Datos primarios + MCP | Verificado en alcance | Catálogo trazable Nexans/INDECO y asignación explícita |
| `ampacity` | Tablas trazables + MCP | Verificado en alcance | P3-v1: filas/factores PRIMARY_VERIFIED CNE y Ib/In/Iz |
| `iec60909` | pandapower | Verificado en alcance | P4-v1: 3F/2F/1F-T MAX/MIN según contrato y fichas admitidas |
| `pandapower_power_flow` | pandapower | En verificación | Puente balanceado líneas/cargas/P2; ext_grid ideal 1 pu |
| `short_circuit` | OpenDSS FaultStudy | Exploratorio | Herramienta exploratoria; no ruta IEC 60909 |
| `protection_data` | Datos/curvas + postproceso MCP | Verificado en alcance | Datos breaker/fuse y vínculo explícito con conductor |
| `tcc_curve_evaluation` | Datos/curvas + postproceso MCP | Verificado en alcance | Interpolación LOG_LOG por segmentos SINGLE/BAND, sin extrapolación |
| `protection_checks` | Datos/curvas + postproceso MCP | Verificado en alcance | Comparación de corte y chequeo adiabático con entradas explícitas |
| `protection_clearing_time` | Datos/curvas + postproceso MCP | Verificado en alcance | TOTAL_CLEARING_TIME con bandas y procedencia conservadas |
| `protection_coordination` | Datos/curvas + postproceso MCP | Verificado en alcance | Margen temporal puntual entre dos dispositivos declarados |
| `reproducible_project` | Persistencia/presentación MCP + OpenDSS cuando reconstruye | Verificado en alcance | Snapshot P7A canónico y verificación de integridad |
| `project_reconstruction` | Persistencia/presentación MCP + OpenDSS cuando reconstruye | Verificado en alcance | Restauración P7B del netlist DSS con round-trip y aislamiento |
| `technical_report` | Persistencia/presentación MCP + OpenDSS cuando reconstruye | Verificado en alcance | Reporte determinista de snapshot verificado y PDF mediante impresión |
| `reactive_compensation` | OpenDSS | Verificado en alcance | Bancos ideales por etapas; verificación cuantitativa balanceada y comparación estática explícita |
| `motor_static` | OpenDSS | Verificado en alcance | P13B/C/D: corriente/fp o estados de arranque explícitos, sin aceleración generada |
| `operating_scenarios` | OpenDSS | Verificado en alcance | P12: contingencias/transferencias/deslastre estáticos declarados |
| `modelica_dol` | OpenModelica/MSL | Verificado en alcance | MSL DOL con equivalente RL equilibrado explícito, resistencias fijas y curva de carga declarada; contraste cuantitativo de una máquina estrella/delta y una/dos máquinas delta con carga |
| `modelica_scr` | OpenModelica/MSL | Verificado en alcance | Una o dos máquinas delta, red RL equilibrada común y controladores genéricos MSL independientes; arranques simultáneos/escalonados en bancos Q4/Q5 |
| `harmonics` | OpenDSS | Verificado en alcance | Red trifasica equilibrada; espectros no triplen de carga y barrido de impedancia de secuencia positiva; R constante/X proporcional a frecuencia |
| `time_series` | OpenDSS | Verificado en alcance | Daily/Yearly nativos en red trifasica equilibrada a 50/60 Hz; perfiles regulares P/Q, repeticion diaria explicita y energia del periodo declarado |
| `relay_operation` | pandapower OCRelay | Verificado en alcance | DTOC/IDMT/IDTOC nativos, ajustes explicitos, puntos independientes de corriente RMS primaria constante; tiempo de rele separado del interruptor |
| `arc_flash_ieee1584` | Por integrar | Diferido por el usuario | Arc Flash formal |
| `arc_flash_lee` | MCP histórico | Educativo | Estimación educativa Lee |
| `professional_report` | Ingeniero responsable | A cargo del ingeniero (fuera del software) | Revisión, aprobación y firma del estudio por el ingeniero; fuera de la calificación técnica del software |
| `custom_motor_physics` | MCP retirado | Retirado | Solvers propios DOL/RK4/SCR retirados |

## Condiciones finitas pendientes

DOL y SCR están verificados dentro de sus alcances documentados. La instalación de MSL no basta para aprobar un adaptador. El motor alternativo pandapower de flujo tampoco bloquea el alcance ya comprobado del motor principal OpenDSS.

### pandapower_power_flow

- **PPF01 — PENDING:** Contrastar transformación P2, taps, carga y pérdidas por terminal contra ejecución nativa pandapower con entradas independientes
- **PPF02 — PENDING:** MCP público debe reproducir esos casos y rechazar equipos no traducibles

## Condiciones cerradas con evidencia

- **power_flow / PF_EXT01 — PASSED:** Seis casos de 33/69 barras contrastados con PYPOWER AC Newton mediante MCP; tolerancias explícitas y datos upstream fijados. No incluye transformadores, desbalance ni redes malladas.
- **power_flow / PF_EXT02 — PASSED:** Ocho casos IEEE4 por fase y 48 variantes controladas de grupos/taps/perdidas contrastados mediante MCP, con fuentes fijadas y tolerancias previas. No califica una instalacion real, SC/protecciones ni regulacion automatica.
- **voltage_drop / VD_EXT01 — PASSED:** Seis casos de 33/69 barras contrastados con PYPOWER AC Newton mediante MCP; tolerancias explícitas y datos upstream fijados. No incluye transformadores, desbalance ni redes malladas.
- **modelica_dol / DOL01 — PASSED:** Reproducir un ejemplo original MSL directamente y por MCP con parámetros/conexiones equivalentes y tolerancias fijadas antes del contraste
- **modelica_dol / DOL02 — PASSED:** Cerrar la convención de temperatura/pérdidas/inercia y conversión de fase para estrella/delta en los casos admitidos
- **modelica_dol / DOL03 — PASSED:** Ejecutar regresión física automatizada con runtime fijado; rechazar solicitudes fuera del equivalente admitido
- **modelica_scr / SCR01 — PASSED:** Cerrar perfil numérico reproducible y robustez de inicialización/eventos sobre rango declarado; justificar o sustituir el solver algebraico prototipo
- **modelica_scr / SCR02 — PASSED:** Contrastar circuito/control completo contra ejemplo MSL original con métricas y tolerancias prefijadas
- **modelica_scr / SCR03 — PASSED:** Verificar referencia de disparo y alcance admitido; mantener bloqueadas estrella y multimáquina hasta pruebas específicas
- **modelica_scr / TWO_SCR01 — PASSED:** Dos ramas sobre una impedancia común: contraste original, equivalencia Z/2Z y KVL con suma de corrientes
- **modelica_scr / TWO_SCR02 — PASSED:** Controladores y bypass independientes; arranques simultáneos, solapados y tras bypass; 50/60 Hz; bloqueos fuera de alcance
- **harmonics / HARM01 — PASSED:** 24 combinaciones RL/C independientes a 50/60 Hz, wye/delta, banco ON/OFF y amortiguamiento 0/50/100%; contraste nativo y 54 llamadas MCP
- **time_series / TS01 — PASSED:** 16 contrastes PQ/Z independientes y nativos a 50/60 Hz, Daily/Yearly y pasos 15/60 min; energia, 8760 h y 39 llamadas MCP
- **relay_operation / RELAY01 — PASSED:** Ajustes nativos sin autograding; curvas y umbrales contrastados contra referencia escalar independiente y serializacion nativa
- **relay_operation / RELAY02 — PASSED:** Ejecucion MCP real, escenarios sc/pp, retardo de interruptor separado y circuito padre intacto

## Evidencia y exclusiones por módulo

### power_flow

Evidencia: [test_benchmarks_p1.py](../tests/test_benchmarks_p1.py), [run_benchmarks_p1.py](../examples/run_benchmarks_p1.py), [test_external_feeder_qualification.py](../tests/test_external_feeder_qualification.py), [verify_external_feeders_mcp.py](../scripts/verify_external_feeders_mcp.py), [CALIFICACION_ALIMENTADORES_EXTERNOS.md](../docs/CALIFICACION_ALIMENTADORES_EXTERNOS.md), [external_feeders_windows.json](../docs/evidence/external_feeders_windows.json), [test_transformer_external_qualification.py](../tests/test_transformer_external_qualification.py), [verify_transformers_mcp.py](../scripts/verify_transformers_mcp.py), [transformer_reference.py](../scripts/transformer_reference.py), [CALIFICACION_TRANSFORMADORES_Q11.md](../docs/CALIFICACION_TRANSFORMADORES_Q11.md), [transformers_q11_linux.json](../docs/evidence/transformers_q11_linux.json).

Fuera del cierre: Otros desbalances y alimentadores IEEE/EPRI completos; Neutros explicitos, regulacion automatica y transitorios de transformadores.

### voltage_drop

Evidencia: [test_benchmarks_p1.py](../tests/test_benchmarks_p1.py), [test_external_feeder_qualification.py](../tests/test_external_feeder_qualification.py), [verify_external_feeders_mcp.py](../scripts/verify_external_feeders_mcp.py), [CALIFICACION_ALIMENTADORES_EXTERNOS.md](../docs/CALIFICACION_ALIMENTADORES_EXTERNOS.md), [external_feeders_windows.json](../docs/evidence/external_feeders_windows.json).

Fuera del cierre: Caída acumulada y desbalance.

### conductor_library

Evidencia: [test_professional_validation.py](../tests/test_professional_validation.py), [P3_BENCHMARK_EVIDENCE.md](../docs/P3_BENCHMARK_EVIDENCE.md).

Fuera del cierre: Catálogo exhaustivo y secuencia cero/geometría.

### ampacity

Evidencia: [P3C12A_INDEPENDENT_BENCHMARKS.md](../docs/P3C12A_INDEPENDENT_BENCHMARKS.md), [P3C12B_PRIMARY_BENCHMARK_GATE.md](../docs/P3C12B_PRIMARY_BENCHMARK_GATE.md).

Fuera del cierre: Otras normas/filas no verificadas; tablas completas.

### iec60909

Evidencia: [P4_BENCHMARK_3PH.md](../docs/P4_BENCHMARK_3PH.md), [test_iec60909_p4c07.py](../tests/test_iec60909_p4c07.py).

Fuera del cierre: Conformidad integral de edición objetivo; Ib/Ik permanente y deberes excluidos.

### pandapower_power_flow

Evidencia: [test_pandapower_engine.py](../tests/test_pandapower_engine.py).

Fuera del cierre: Generadores, motores, desbalance; no se necesita para cerrar el flujo principal OpenDSS.

### short_circuit

Evidencia: [test_professional_validation.py](../tests/test_professional_validation.py).

Fuera del cierre: Uso IEC delegado al módulo pandapower; no duplicar esta calificación.

### protection_data

Evidencia: [test_p5a_protection_data.py](../tests/test_p5a_protection_data.py), [run_benchmarks_p5g.py](../examples/run_benchmarks_p5g.py), [test_p10f_reference_protection.py](../tests/test_p10f_reference_protection.py).

Fuera del cierre: Selectividad integral, actuación de relés, backup/cascading; Conformidad normativa integral y datasets automáticos k.

### tcc_curve_evaluation

Evidencia: [test_p5b_tcc_curves.py](../tests/test_p5b_tcc_curves.py), [run_benchmarks_p5g.py](../examples/run_benchmarks_p5g.py), [test_p10f_reference_protection.py](../tests/test_p10f_reference_protection.py).

Fuera del cierre: Selectividad integral, actuación de relés, backup/cascading; Conformidad normativa integral y datasets automáticos k.

### protection_checks

Evidencia: [test_p5c_protection_checks.py](../tests/test_p5c_protection_checks.py), [run_benchmarks_p5g.py](../examples/run_benchmarks_p5g.py), [test_p10f_reference_protection.py](../tests/test_p10f_reference_protection.py).

Fuera del cierre: Selectividad integral, actuación de relés, backup/cascading; Conformidad normativa integral y datasets automáticos k.

### protection_clearing_time

Evidencia: [test_p5d_clearing_time.py](../tests/test_p5d_clearing_time.py), [run_benchmarks_p5g.py](../examples/run_benchmarks_p5g.py), [test_p10f_reference_protection.py](../tests/test_p10f_reference_protection.py).

Fuera del cierre: Selectividad integral, actuación de relés, backup/cascading; Conformidad normativa integral y datasets automáticos k.

### protection_coordination

Evidencia: [test_p5e_temporal_coordination.py](../tests/test_p5e_temporal_coordination.py), [run_benchmarks_p5g.py](../examples/run_benchmarks_p5g.py), [test_p10f_reference_protection.py](../tests/test_p10f_reference_protection.py).

Fuera del cierre: Selectividad integral, actuación de relés, backup/cascading; Conformidad normativa integral y datasets automáticos k.

### reproducible_project

Evidencia: [test_p7a_project_snapshot.py](../tests/test_p7a_project_snapshot.py), [test_p7d_engineering_preview.py](../tests/test_p7d_engineering_preview.py).

Fuera del cierre: Restauración automática P2/P3/P5 y vista; firma/aprobación del informe.

### project_reconstruction

Evidencia: [test_p7b_project_reconstruction.py](../tests/test_p7b_project_reconstruction.py), [test_p7d_engineering_preview.py](../tests/test_p7d_engineering_preview.py).

Fuera del cierre: Restauración automática P2/P3/P5 y vista; firma/aprobación del informe.

### technical_report

Evidencia: [test_p7c_project_report.py](../tests/test_p7c_project_report.py), [test_p7d_engineering_preview.py](../tests/test_p7d_engineering_preview.py).

Fuera del cierre: Restauración automática P2/P3/P5 y vista; firma/aprobación del informe.

### reactive_compensation

Evidencia: [test_reactive_compensation.py](../tests/test_reactive_compensation.py), [verify_reactive_compensation_mcp.py](../scripts/verify_reactive_compensation_mcp.py), [verify_module_qualification_mcp.py](../scripts/verify_module_qualification_mcp.py).

Fuera del cierre: Armónicos, reactores, CapControl, desbalance y selección integral.

### motor_static

Evidencia: [test_p13b_static_motor_starting.py](../tests/test_p13b_static_motor_starting.py), [test_p13c_motor_starting_profiles.py](../tests/test_p13c_motor_starting_profiles.py), [test_p13d_motor_starting_sequences.py](../tests/test_p13d_motor_starting_sequences.py).

Fuera del cierre: Dinámica y controles de arrancador.

### operating_scenarios

Evidencia: [test_p12_operating_scenarios.py](../tests/test_p12_operating_scenarios.py), [test_p12e_alternative_source_transfer.py](../tests/test_p12e_alternative_source_transfer.py), [test_p12d_mcp_scenario_tools.py](../tests/test_p12d_mcp_scenario_tools.py).

Fuera del cierre: Optimización de contingencias y transferencia dinámica/sincronismo.

### modelica_dol

Evidencia: [verify_modelica_motor_adapter_mcp.py](../scripts/verify_modelica_motor_adapter_mcp.py), [test_modelica_motor_adapter.py](../tests/test_modelica_motor_adapter.py), [msl_dol_native_reference.py](../scripts/msl_dol_native_reference.py), [verify_msl_dol_qualification_mcp.py](../scripts/verify_msl_dol_qualification_mcp.py), [msl_motor_dol_native_reference.json](../examples/msl_motor_dol_native_reference.json), [MSL_DOL_VERIFICACION.md](../docs/MSL_DOL_VERIFICACION.md).

Fuera del cierre: Traducción automática del unifilar completo, cargas de potencia constante de fondo, variadores y calentamiento/saturación; Calificación del proyecto con fichas reales; todas las combinaciones de las hasta ocho máquinas admitidas; SCR se califica por separado.

### modelica_scr

Evidencia: [verify_msl_scr_mcp.py](../scripts/verify_msl_scr_mcp.py), [verify_msl_triac_reference.py](../scripts/verify_msl_triac_reference.py), [MSL_SCR_VERIFICACION.md](../docs/MSL_SCR_VERIFICACION.md), [verify_msl_scr_solver_profiles.py](../scripts/verify_msl_scr_solver_profiles.py), [test_modelica_motor_adapter.py](../tests/test_modelica_motor_adapter.py), [msl_scr_native_reference.py](../scripts/msl_scr_native_reference.py), [verify_msl_scr_native_mcp.py](../scripts/verify_msl_scr_native_mcp.py), [check_msl_scr_trace.py](../scripts/check_msl_scr_trace.py), [msl_scr_native_evidence_v1.json](../mcp_electrico/data/msl_scr_native_evidence_v1.json), [MSL_SCR_REFERENCIA_ORIGINAL.md](../docs/MSL_SCR_REFERENCIA_ORIGINAL.md), [verify_msl_scr_two_mcp.py](../scripts/verify_msl_scr_two_mcp.py), [verify_msl_scr_two_60_mcp.py](../scripts/verify_msl_scr_two_60_mcp.py), [verify_msl_scr_two_loaded_mcp.py](../scripts/verify_msl_scr_two_loaded_mcp.py), [test_scr_two_oracles.py](../tests/test_scr_two_oracles.py), [msl_two_scr_evidence_v1.json](../mcp_electrico/data/msl_two_scr_evidence_v1.json), [MSL_SCR_DOS_MOTORES.md](../docs/MSL_SCR_DOS_MOTORES.md).

Fuera del cierre: Control real de fabricante; SCR estrella; más de dos máquinas SCR; combinaciones DOL/SCR; traducción automática del unifilar.

### harmonics

Evidencia: [test_harmonics.py](../tests/test_harmonics.py), [harmonics_reference.py](../scripts/harmonics_reference.py), [verify_harmonics_mcp.py](../scripts/verify_harmonics_mcp.py), [harmonics_transformer_native.dss](../examples/harmonics_transformer_native.dss), [ARMONICOS_OPENDSS.md](../docs/ARMONICOS_OPENDSS.md).

Fuera del cierre: Triplen/secuencia cero y desbalance; Armónicos de tensión de fondo e interarmónicos de emisión; Efecto pelicular, filtros desintonizados y transitorios; Conformidad IEEE 519 automática; pico exacto de resonancia sin refinamiento.

### time_series

Evidencia: [test_time_series.py](../tests/test_time_series.py), [time_series_reference.py](../scripts/time_series_reference.py), [verify_time_series_mcp.py](../scripts/verify_time_series_mcp.py), [SERIES_TEMPORALES_OPENDSS.md](../docs/SERIES_TEMPORALES_OPENDSS.md).

Fuera del cierre: Desbalance, generacion y almacenamiento; Control automatico, bancos y topologia variable; Perfiles irregulares/incompletos y extrapolacion anual automatica; EMT y aceleracion de motores.

### relay_operation

Evidencia: [test_relay_operation.py](../tests/test_relay_operation.py), [relay_operation_reference.py](../scripts/relay_operation_reference.py), [verify_relay_operation_mcp.py](../scripts/verify_relay_operation_mcp.py), [relay_operation_q8_mcp.json](../docs/evidence/relay_operation_q8_mcp.json), [ACTUACION_RELES_PANDAPOWER.md](../docs/ACTUACION_RELES_PANDAPOWER.md).

Fuera del cierre: Corrientes variables, saturacion CT y formas de onda secundarias; Recalculo de red tras apertura, secuencia de disparos, recierre y fallo de interruptor; Selectividad integral, ajustes automaticos y calificacion de fabricante; Vinculacion automatica de corrientes P4; protecciones direccionales y de tierra.

### arc_flash_ieee1584

Evidencia: [ROADMAP_PROFESIONAL.md](../docs/ROADMAP_PROFESIONAL.md).

### arc_flash_lee

Evidencia: [test_professional_validation.py](../tests/test_professional_validation.py).

Fuera del cierre: No reemplaza IEEE 1584; fuera del cierre industrial actual.

### professional_report

Evidencia: [P7_ENGINEERING_PREVIEW.md](../docs/P7_ENGINEERING_PREVIEW.md).

Fuera del cierre: La firma digital integrada es una función opcional de gestión documental; no un requisito para confiar en un cálculo verificado.

### custom_motor_physics

Evidencia: [verify_modelica_motor_adapter_mcp.py](../scripts/verify_modelica_motor_adapter_mcp.py).

## Orden del roadmap

1. DOL cerrado en alcance: conservar su regresión contra el ejemplo original MSL y sus convenciones.
2. Conservar la regresión SCR y el alcance de máquinas/controladores indicado en el registro; ampliar otras conexiones y configuraciones solo después de sus pruebas.
3. Armónicos Q6, perfiles Q7 y actuación OCRelay Q8 cerrados en sus alcances; conservar las regresiones publicadas.
4. Mejorar gráficos/informes y realizar estudios con datos reales y criterios acordados. Arc Flash continúa diferido.
5. El flujo alternativo pandapower permanece en verificación; ampliarlo solo si una necesidad concreta justifica su alcance, manteniendo OpenDSS como ruta principal ya comprobada.

Una ficha de fabricante o la validación de un proyecto se exige al usar ese equipo; no es condición interminable para cerrar toda integración genérica. Los criterios se acuerdan por estudio y no se inventan mínimos normativos universales.
