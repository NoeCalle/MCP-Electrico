# Estado de cierre de módulos

Revisión: **Q1_2026_10_03**. Fuente: `mcp_electrico/data/module_qualification_v1.json`.

Documento generado con `scripts/render_module_qualification.py`; la prueba de sincronización impide publicar estados divergentes.

## Qué se cierra

Se cierra la integración dentro del alcance demostrado por las pruebas citadas. El respaldo del motor abierto no comprueba por sí solo las unidades, conexiones, traducción de datos y lectura de resultados del adaptador MCP.

Los seis estados se evalúan por separado: verificación de integración, alcance soportado, preparación de datos del proyecto, criterios de diseño, conformidad normativa y aprobación del informe. Un módulo verificado puede recibir un proyecto incompleto o calcular un diseño que incumple sus criterios.

Las nueve promociones Q1 son bancos estáticos, los cinco componentes P5 y los tres componentes P7. Su madurez pública es `VALIDATED_WITH_LIMITATIONS`, con el estado anterior como procedencia. Las ampliaciones excluidas no vuelven a abrir el alcance cerrado.

`professional_emission=false` se mantiene. El gate actual del producto se consulta con `evaluar_cierre_p7d_engineering_preview`; los flags históricos de componentes P5/P7 no conceden una habilitación global. Un snapshot conserva la calificación de su fecha de captura.

## Registro actual

| Módulo | Motor | Estado | Alcance comprobado o solicitado |
|---|---|---|---|
| `power_flow` | OpenDSS | Verificado en alcance | Radial trifásico equilibrado de dos barras PQ |
| `voltage_drop` | OpenDSS + postproceso | Verificado en alcance | Caída por Line en el alcance P1 |
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
| `modelica_dol` | OpenModelica/MSL | En verificación | Máquinas DOL sobre equivalente RL equilibrado común; casos sintéticos ejecutados |
| `modelica_scr` | OpenModelica/MSL | En verificación | Una máquina delta y controlador MSL genérico; evidencia sintética |
| `harmonics` | OpenDSS | Pendiente de integración | Armónicos y resonancia |
| `time_series` | OpenDSS | Pendiente de integración | Daily/Yearly con perfiles explícitos |
| `relay_operation` | pandapower OCRelay | Pendiente de integración | Actuación de relés |
| `arc_flash_ieee1584` | Por integrar | Diferido por el usuario | Arc Flash formal |
| `arc_flash_lee` | MCP histórico | Educativo | Estimación educativa Lee |
| `professional_report` | Flujo de aprobación por implementar | Pendiente de integración | Firma y aprobación profesional del informe |
| `custom_motor_physics` | MCP retirado | Retirado | Solvers propios DOL/RK4/SCR retirados |

## Condiciones finitas pendientes

La dinámica DOL y SCR conserva `IN_VERIFICATION`: hay ejecuciones sintéticas, pero todavía falta cerrar las condiciones siguientes. No se anuncia como módulo plenamente verificado por tener MSL instalada. El motor alternativo pandapower de flujo tampoco bloquea el alcance ya comprobado del motor principal OpenDSS.

### pandapower_power_flow

- **PPF01 — PENDING:** Contrastar transformación P2, taps, carga y pérdidas por terminal contra ejecución nativa pandapower con entradas independientes
- **PPF02 — PENDING:** MCP público debe reproducir esos casos y rechazar equipos no traducibles

### modelica_dol

- **DOL01 — PENDING:** Reproducir un ejemplo original MSL directamente y por MCP con parámetros/conexiones equivalentes y tolerancias fijadas antes del contraste
- **DOL02 — PENDING:** Cerrar la convención de temperatura/pérdidas/inercia y conversión de fase para estrella/delta en los casos admitidos
- **DOL03 — PENDING:** Ejecutar regresión física automatizada con runtime fijado; rechazar solicitudes fuera del equivalente admitido

### modelica_scr

- **SCR01 — PENDING:** Cerrar perfil numérico reproducible y robustez de inicialización/eventos sobre rango declarado; justificar o sustituir el solver algebraico prototipo
- **SCR02 — PENDING:** Contrastar circuito/control completo contra ejemplo MSL original con métricas y tolerancias prefijadas
- **SCR03 — PENDING:** Verificar referencia de disparo y alcance admitido; mantener bloqueadas estrella y multimáquina hasta pruebas específicas

### harmonics

- **ADAPTER — PENDING:** Integrar datos y ejecución nativa del motor, contrastar referencia reproducible por MCP y publicar límites

### time_series

- **ADAPTER — PENDING:** Integrar datos y ejecución nativa del motor, contrastar referencia reproducible por MCP y publicar límites

### relay_operation

- **ADAPTER — PENDING:** Integrar datos y ejecución nativa del motor, contrastar referencia reproducible por MCP y publicar límites

## Evidencia y exclusiones por módulo

### power_flow

Evidencia: [test_benchmarks_p1.py](../tests/test_benchmarks_p1.py), [run_benchmarks_p1.py](../examples/run_benchmarks_p1.py).

Fuera del cierre: Desbalance y alimentadores IEEE/EPRI completos.

### voltage_drop

Evidencia: [test_benchmarks_p1.py](../tests/test_benchmarks_p1.py).

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

Evidencia: [verify_modelica_motor_adapter_mcp.py](../scripts/verify_modelica_motor_adapter_mcp.py), [test_modelica_motor_adapter.py](../tests/test_modelica_motor_adapter.py).

Fuera del cierre: Traducción completa del unifilar; calificación de proyecto con fichas reales.

### modelica_scr

Evidencia: [verify_msl_scr_mcp.py](../scripts/verify_msl_scr_mcp.py), [verify_msl_triac_reference.py](../scripts/verify_msl_triac_reference.py), [MSL_SCR_VERIFICACION.md](../docs/MSL_SCR_VERIFICACION.md).

Fuera del cierre: Reproducción de control de fabricante; SCR estrella/multimotor.

### harmonics

Evidencia: [MIGRACION_MODELOS_ABIERTOS.md](../docs/MIGRACION_MODELOS_ABIERTOS.md).

### time_series

Evidencia: [MIGRACION_MODELOS_ABIERTOS.md](../docs/MIGRACION_MODELOS_ABIERTOS.md).

### relay_operation

Evidencia: [MIGRACION_MODELOS_ABIERTOS.md](../docs/MIGRACION_MODELOS_ABIERTOS.md).

### arc_flash_ieee1584

Evidencia: [ROADMAP_PROFESIONAL.md](../docs/ROADMAP_PROFESIONAL.md).

### arc_flash_lee

Evidencia: [test_professional_validation.py](../tests/test_professional_validation.py).

Fuera del cierre: No reemplaza IEEE 1584; fuera del cierre industrial actual.

### professional_report

Evidencia: [P7_ENGINEERING_PREVIEW.md](../docs/P7_ENGINEERING_PREVIEW.md).

Fuera del cierre: Es un proceso de emisión separado de la exactitud de cálculos.

### custom_motor_physics

Evidencia: [verify_modelica_motor_adapter_mcp.py](../scripts/verify_modelica_motor_adapter_mcp.py).

## Orden del roadmap

1. Cerrar DOL con referencia MSL original, convenciones de máquina y regresión reproducible del alcance admitido.
2. Cerrar SCR para una máquina delta: inicialización y eventos, referencia completa y control admitido. Estrella y multimotor requieren sus pruebas propias antes de ampliarse.
3. Revisar el flujo alternativo pandapower solo si una necesidad concreta justifica su alcance. Mantener OpenDSS como ruta principal ya comprobada.
4. Después de esos cierres, integrar armónicos/perfiles/relés que falten usando motores existentes, sin duplicar solvers suficientes.
5. Mejorar la presentación y realizar pilotos con datos reales y criterios acordados. Arc Flash continúa diferido.

Una ficha de fabricante o la validación de un proyecto se exige al usar ese equipo; no es condición interminable para cerrar toda integración genérica. Los criterios se acuerdan por estudio y no se inventan mínimos normativos universales.
