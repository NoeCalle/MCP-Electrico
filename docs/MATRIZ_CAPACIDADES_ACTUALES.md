# Matriz de capacidades actuales — MCP Eléctrico


**Ampliación Q5 (4 de octubre):** dos motores SCR delta sobre red RL común verificados mediante siete estudios, 50/60 Hz, cargas distintas y bypass independientes. Ver [alcance y evidencia](MSL_SCR_DOS_MOTORES.md). Más de dos SCR, mezcla DOL/SCR y estrella siguen fuera del alcance.

## Confiabilidad técnica y responsabilidad del ingeniero — Q5

El MCP es una herramienta de cálculo para el ingeniero. Su desarrollo debe demostrar
que las entradas se traducen correctamente, que los resultados son reproducibles
y contrastados, y que los datos faltantes, supuestos, límites y errores se informan.
El ingeniero selecciona los criterios del proyecto, revisa los resultados,
aprueba el estudio y lo firma. Esa aprobación es una responsabilidad externa;
no es un módulo numérico pendiente de implementar.

Los campos históricos `professional_emission=false` y `professional_report=false`
indican que el software no aprueba ni firma automáticamente. No prohíben el uso
profesional del cálculo ni la firma del ingeniero. Una firma digital integrada
sería una mejora documental opcional y no una condición para verificar un solver.
Los estados experimentales se conservan exclusivamente cuando falta evidencia
técnica de la integración o del alcance. Arc Flash permanece diferido.

**Fecha:** 4 de octubre de 2026. Actualización Q5: DOL y SCR verificados dentro de sus alcances publicados. Ver [registro de cierre](ESTADO_CIERRE_MODULOS.md).
El servidor actualizado registra **154 herramientas**. Bancos estáticos añaden
22 llamadas MCP y 24 comparaciones independientes; ver
[compensación reactiva](COMPENSACION_REACTIVA_OPENDSS.md). La evidencia stdio de
migración incluye 12 llamadas y tres simulaciones sintéticas MSL, con
refinamiento y un oráculo independiente. La suite MCP general y la disponibilidad
de las herramientas en este chat son comprobaciones separadas.

Q2: 22 llamadas MCP, siete casos DOL y cuatro contrastes con el ejemplo original MSL;
ver [evidencia y convenciones DOL](MSL_DOL_VERIFICACION.md). Estos casos no son fichas de las bombas del proyecto.

Q5: siete estudios de extensión SCR (seis de dos motores y un control), 18 llamadas MCP, 14 trazas y 26 comprobaciones por máquina. Suite general: 968 aprobadas y una omitida; CI de #163: 77 aprobadas. Ver [dos SCR](MSL_SCR_DOS_MOTORES.md) y [estado actual](ESTADO_ACTUAL.md).

Ver [migración y necesidades industriales](MIGRACION_MODELOS_ABIERTOS.md).

## Cómo leer la matriz

**Dirección de desarrollo:** integrar herramientas gratuitas y abiertas
existentes antes de implementar física propia. La matriz describe lo que hoy
está implementado; existe ejecución DOL verificada en alcance de OpenModelica/MSL por MCP para un
equivalente RL de barra común. SCR está verificado para una o dos máquinas delta con controles genéricos MSL independientes.
Ver [arquitectura de integración](ARQUITECTURA_INTEGRACION.md).

El selector determinista conserva ocho rutas genéricas de planificación, tres con adaptadores acotados DOL/SCR verificados, y un catálogo
de modelos abiertos: [investigación y reglas](MOTORES_ABIERTOS_INVESTIGACION.md).
Las rutas genéricas no traducen automáticamente el unifilar. El adaptador MSL se ejecuta con paquete explícito; ver [selección vigente](ENGINE_SELECTION.md).

- **OpenDSS**: solver principal de red. **pandapower**: segundo solver, especialmente cortocircuito IEC 60909. **Módulo propio MCP**: lógica de datos, cálculo específico, control, criterios y documentación.
- Una fila con aportes de dos columnas significa que trabajan juntos en ese estudio; no significa que dos solvers estén contrastando el mismo resultado.
- **Disponible** significa que existe ejecución dentro del alcance descrito. **Validado con limitaciones** identifica verificación dentro de un alcance concreto. **Experimental/en validación** requiere conservar esa condición al interpretar resultados. **Pendiente** significa que no está cubierto por el módulo vigente.
- La disponibilidad no significa que un proyecto tenga los datos necesarios ni que cumpla sus criterios. Los datos típicos aprobados se identifican como supuestos; no pasan a ser datos reales del fabricante.
- Un cálculo finalizado, un criterio cumplido, un modelo validado y la emisión de un informe profesional son comprobaciones diferentes.

## Estado del SCR

El equivalente físico propio SCR/RL se retiró. MSL ejecuta el estudio verificado en alcance
de una o dos máquinas delta, con red RL común explícita, realimentación de corriente y bypass
automático. El solver/control de referencia no califica un arrancador de fabricante.
Estrella, más de dos motores SCR y combinaciones DOL/SCR permanecen bloqueados. Las tensiones de barra y terminal
se presentan por separado. Los contrastes anteriores son históricos y no validan
M1/M2. Q4 añade seis contrastes con el ejemplo original MSL y comprobaciones independientes de energía y bypass en doce trazas. Ver [verificación](MSL_SCR_VERIFICACION.md) y [referencia original](MSL_SCR_REFERENCIA_ORIGINAL.md).

## Qué significa dinámica simultánea

Ejemplo: M1 empieza en t=0 s; M2 empieza en t=2 s mientras M1 aún acelera. Ambos cambian su velocidad, par y corriente; la tensión común afecta la aceleración de ambos, y sus corrientes vuelven a afectar la tensión. La simulación debe integrar los dos motores junto con la red en cada instante.

El adaptador MSL DOL verificado en alcance conecta varias máquinas a la misma red RL
declarada; se probaron dos motores con arranques en t=0 y t=2 s.
Q5 también comprobó dos SCR con órdenes simultáneas, solapadas y después del bypass de M1, a 50/60 Hz y con cargas distintas. Los solucionadores propios P13F/P13G se retiraron. P13D sí resuelve estados conjuntos de varios motores con sus demandas declaradas, incluso puntos simultáneos de arranque, pero no calcula su evolución mecánica conjunta. Un motor acelerando con otro representado como carga de marcha tampoco equivale a integrar dos motores dinámicos.

## Matriz completa por funcionalidad

“—” indica que ese motor no participa en la implementación actual de la fila, no que sea incapaz en otras aplicaciones.

### 1. Modelo y datos

| Función | OpenDSS | pandapower | Módulo propio MCP | Estado actual | Límite principal |
|---|---|---|---|---|---|
| Crear y editar una red | Modelo eléctrico | Proyección posterior cuando aplica | Construcción, fichas y estados | Disponible | Fuente, líneas, cargas, transformadores y generador OpenDSS; no supone soporte de cualquier equipo. |
| Construcción Rev.0 con datos pendientes | Materializa elementos admitidos | — | Admisión y registro de pendientes | Disponible; sin resolver | Un elemento pendiente no se inventa ni se introduce al solver; puede bloquear el estudio que depende de él. |
| Datos profesionales de fuente y transformadores | Recibe datos explícitos | Consume fichas para puente P2/P4 | Procedencia y suficiencia | P2 completo con limitaciones | Tensiones, potencia, impedancias, pérdidas, taps y conexiones dependen de la ficha y del estudio. |
| Catálogo y asignación de cables | Usa impedancia asignada | Usa datos proyectables | Biblioteca trazable y asignaciones | Validado con limitaciones | Catálogo Nexans/INDECO reducido; no reemplaza X faltante ni aporta todas las geometrías/R0/X0. |
| Secuencia cero y puesta a tierra | Usa datos según estudio | Usa datos en fallas a tierra | Fichas de fuente, línea y transformador | Disponible dentro del alcance P4 | R0/X0/C0, conexiones y neutros deben declararse; no basta con la impedancia positiva. |
| Auditoría y preparación del estudio | — | — | Control de datos, alcance y revisión | Disponible | Preparado para calcular y cumplir criterios son estados distintos. No reemplaza la revisión de entradas por el ingeniero. |

### 2. Flujo de potencia y operación

| Función | OpenDSS | pandapower | Módulo propio MCP | Estado actual | Límite principal |
|---|---|---|---|---|---|
| Flujo de potencia principal | Resuelve tensiones, corrientes y potencias | — | Postproceso y presentación | Validado con limitaciones | La validación independiente P1 cubre redes radiales balanceadas de dos barras PQ; no toda la capacidad de OpenDSS. |
| Flujo con motor alternativo | Origen del modelo activo | Resuelve flujo balanceado | Puente de datos | Experimental | Líneas/cargas trifásicas y transformadores P2; no traduce todavía motores, generadores ni redes desbalanceadas. Fuente de flujo ideal a 1 pu. |
| Caída de tensión | Resuelve tensiones | — | Calcula caída y compara criterio | Validado con limitaciones | Validación P1 por Line en red radial balanceada; caída acumulada/desbalanceada pendiente de benchmark. Umbral declarado. |
| Flujo detallado y cargabilidad | Resultados por alimentador/equipo | — | Indicadores y revisión del workspace | Disponible dentro del alcance del flujo | Para afirmar sobrecarga necesita resultado convergente, rating aplicable y configuración. No convergencia sola no demuestra sobrecarga. |
| Compensación reactiva y bancos por etapas | Capacitor nativo y flujo aislado | — | Datos, escenarios, criterios, balances e informe | Verificado en alcance estático | Red equilibrada pasiva, etapas fijas ideales; sin armónicos, resonancia, reactores, control automático ni selección integral. |
| Escenarios y contingencias N-1 declaradas | Resuelve cada configuración | — | Aperturas/cierres, cargas, continuidad y criterios | P12 foundation disponible | No selecciona automáticamente todas las contingencias ni optimiza maniobras/deslastre. El conjunto evaluado debe representar el alcance solicitado. |
| Deslastre y fuentes alternativas | Equivalente de fuente Vsource | — | Aplica acciones explícitas y restaura la base | Disponible, análisis estático | Transferencia con apertura previa; sin paralelo durante transferencia, sincronización, control AVR/gobernador ni transitorios. Las cargas críticas deben protegerse en las reglas del caso. |

### 3. Cortocircuito

| Función | OpenDSS | pandapower | Módulo propio MCP | Estado actual | Límite principal |
|---|---|---|---|---|---|
| Falla exploratoria FaultStudy | Calcula FaultStudy | — | Controles y visualización | En validación | No equivale al alcance IEC 60909 de pandapower. |
| Trifásico IEC 60909 MAX/MIN | — | Calcula Ik'' y corrientes por rama | Preparación, revisión y presentación | P4-v1 validado con limitaciones | Datos de fuente, líneas, transformadores y temperaturas MIN explícitos. La revisión debe quedar vinculada al modelo; no valida protecciones por sí solo. |
| Bifásico fase-fase IEC 60909 MAX/MIN | — | Calcula falla 2F | Controles y presentación | P4-v1 validado con limitaciones | Política Z2=Z1 solamente en la red simétrica pasiva soportada. |
| Monofásico a tierra IEC 60909 MAX/MIN | — | Calcula falla 1F-T | Validación de secuencia cero y presentación | P4-v1 validado con limitaciones | Requiere secuencia cero y neutros; no promociona ip/Ith en este alcance. |
| Bifásico a tierra MAX/MIN: extensión P4-v1.1 | — | Extrae impedancias Z1/Z0 | Resuelve componentes simétricas y corrientes de fase/tierra | Uso técnico interno con alcance declarado | Falla franca b-c-tierra, Z2=Z1 en red pasiva simétrica. Contraste externo y validación normativa pendientes; no Ik'' contractual ni Sk''/ip/Ith promovidos. |
| Aporte de motores y generadores a falla 3F | Inventario del modelo | Calcula aporte inicial con fichas SC | Clasificación de cargas y admisión | Extensión disponible de P4, alcance limitado | Inducción directa y generador síncrono con fichas. MAX incluye motores conectados; MIN excluye inducción. No aporta variadores por inferirlos desde MW/fp. |
| Pico ip y térmica equivalente Ith | — | Calcula dentro del alcance permitido | Controles de topología y duración | Disponible con exclusiones | Sólo 3F/2F sin máquinas SC y con topology/tk_s/kappa_method explícitos. No es tiempo real de actuación ni calentamiento dinámico del cable. |

### 4. Cables y protecciones

| Función | OpenDSS | pandapower | Módulo propio MCP | Estado actual | Límite principal |
|---|---|---|---|---|---|
| Ampacidad y relación Ib ≤ In ≤ Iz | Puede aportar Ib si se acepta el flujo | — | Calcula capacidad corregida y verifica relación | P3-v1 validado con limitaciones | CNE Utilización 2006 dentro de filas y factores verificados; coincidencia exacta. IEC 60364-5-52 sigue como referencia, sin dataset normativo validado. |
| Evidencia y aplicabilidad de ampacidad | — | — | Referencias, datasets y evidencias primarias | Disponible con cobertura limitada | No hay búsqueda normativa automática ni interpolación de tablas. Combinaciones no demostradas se bloquean o exigen evidencia explícita. |
| Dispositivos, ajustes y curvas TCC | — | — | Registro y evaluación de curvas explícitas | Verificado en alcance; P5 completado con límites | Interruptores y fusibles. Interpolación dentro de segmentos y bandas; no inventa curvas ni ajustes de fabricante. |
| Capacidad de corte de la protección | — | Puede aportar corriente de falla | Compara capacidad declarada con corriente | Verificado en alcance declarado | Icu explícito para interruptor, capacidad de corte para fusible; Ics/Icw no sustituyen Icu. |
| Soportabilidad térmica adiabática del conductor | — | Puede aportar corriente de falla | Verifica I²t ≤ k²S² | Verificado en alcance declarado | Corriente, despeje, k, sección y procedencia explícitos; no evolución térmica detallada. |
| Tiempo final de despeje | — | — | Evalúa/promueve TOTAL_CLEARING_TIME | Verificado en alcance declarado | Tiempo de disparo, fusión u operación no se convierten solos en despeje total; conserva banda min/max. |
| Coordinación temporal entre dos protecciones | — | Puede aportar corrientes por dispositivo | Compara tiempos aguas abajo/arriba | Verificado en alcance declarado | Evaluación puntual con relación declarada y margen conservador. Sin barrido de todo el dominio ni demostración de selectividad integral. |

### 5. Motores y arranque

| Función | OpenDSS | pandapower | Módulo propio MCP | Estado actual | Límite principal |
|---|---|---|---|---|---|
| Caída estática de tensión durante arranque | Resuelve antes/durante con impedancia equivalente | — | Convierte corriente/fp explícitos y compara criterios | Disponible, aproximación estática | Acepta etiquetas DOL/SCR/estrella-triángulo/autotransformador/VFD, pero no simula sus controles ni obtiene aceleración con esas etiquetas. |
| Perfil de arranque por puntos declarados | Resuelve cada punto | — | Ordena puntos proporcionados y compara resultados | Disponible, estático | El tiempo etiqueta los puntos. No integra movimiento ni genera automáticamente corriente/velocidad. |
| Secuencia de varios motores por estados declarados | Resuelve cada estado conjunto | — | Combina apagado/marcha/punto de arranque | Disponible, estático | Puede representar varios motores en un estado de arranque dado; no calcula cómo aceleran juntos ni optimiza el orden. |
| Aceleración dinámica con arranque directo DOL | — | — | Configura componentes Modelica/MSL y procesa CSV | Verificado en alcance MSL DOL | Equivalente RL común explícito; datos SI y curva de carga. Sin traducción automática de todo el unifilar; revisión del estudio por el ingeniero. |
| Aceleración con arranque suave SCR | — | — | Ejecuta componentes MSL y procesa trazas; sin física propia | Verificado en alcance genérico MSL SCR | Una o dos máquinas delta/red RL común/controles MSL; sin calificación de fabricante. Estrella, más de dos motores y DOL/SCR bloqueados. |
| Contraste estructural del equivalente SCR retirado | — | — | Conserva evidencia histórica | Ejecución de comparación retirada | Ya no vuelve a calcular el surrogate eliminado. El contraste histórico de trazas externas sigue legible. |
| Contraste externo de dinámica con motor Modelica | Produce amplitud de fuente del candidato | — | Verifica expediente externo y compara RMS/par/velocidad | Disponible para caso sintético; discrepancia registrada | MSL 4.0.0/OpenModelica 1.27.1 ejecutados aparte. Entradas reproducidas, bypass impuesto; no valida red/control en lazo cerrado ni fabricante. |

### 6. Visualización, informes y uso local

| Función | OpenDSS | pandapower | Módulo propio MCP | Estado actual | Límite principal |
|---|---|---|---|---|---|
| Unifilar técnico y workspace | Aporta modelo/resultados | Aporta resultados de estudios soportados | SVG/HTML, inspector y vistas | Disponible | Presenta datos y resultados ligados a revisión; navegador no calcula ingeniería. No sustituye editor CAD completo. |
| Navegación, etiquetas y láminas de redes grandes | — | — | Presentación y exportación de láminas A3 | Disponible con límites V7.1 | Láminas con solape y numeración; hasta 200 por exportación. PDF mediante impresión, sin nuevos cálculos. |
| Snapshot y reconstrucción | Guarda/recompila netlist DSS | — | Hashes, aislamiento y comparación de archivos | Verificado en alcance; P7 mínimo cerrado | P7B restaura netlist, no todos los estados P2/P3/P5 ni la presentación. Requiere re-vincular datos y recalcular resultados. |
| Reporte técnico reproducible | — | — | Renderiza snapshot verificado | Verificado en alcance declarado | HTML preparado para impresión/PDF por navegador; no PDF nativo, firma, sello o aprobación profesional. |
| Expedientes de proyecto, escenarios y arranque | Resuelve según estudio | Se usa según estudio | Gráficas/tablas/CSV/JSON, replay e integridad | Disponible dentro del alcance de cada estudio | Resultados, fuentes y limitaciones conservados. Verificar integridad no valida físicamente entradas o supuestos. |
| Admisión de proyecto real y uso local | Backend local | Backend local | Checklist, gates y servidor | Engineering Preview local disponible | Windows; stdio y HTTP de loopback. La consulta de este catálogo no confirma por sí sola la conexión de este chat ni instalación remota. |
| Arc flash simplificado de Lee | — | — | Estimación simplificada | Experimental/educativo | calcular_arc_flash es un alias de Lee. Ninguno implementa IEEE 1584. |

## Capacidades pendientes o fuera del alcance

| Función | Estado | Qué falta / distinción importante |
|---|---|---|
| Dinámica de varios motores acoplados del unifilar completo | Calificación integral pendiente | DOL MSL de equivalente RL común verificado en alcance, probado con dos motores; SCR con dos motores verificado; traducción completa, más de dos SCR y mezcla DOL/SCR excluidas. |
| SCR trifásico cualificado para un dispositivo real | Datos y contraste del dispositivo real pendientes; controlador genérico verificado | SCR01–SCR03 cerrados para controlador genérico MSL. Las discrepancias del equivalente propio retirado son históricas; la ficha y el contraste de fabricante corresponden al dispositivo real. |
| Dinámica de VFD, estrella-triángulo y autotransformador | No implementada | Las etiquetas admitidas por el cálculo estático no modelan control, conmutación ni aceleración de esos sistemas. |
| Armónicos y calidad de energía | No expuesto/validado como módulo de estudio | La capacidad del solver OpenDSS no equivale a una herramienta MCP disponible; el SCR actual no calcula distorsión de toda la red. |
| EMT general, saturación y calentamiento dinámico | Sin adaptador general / extensiones excluidas | MSL sí simula señales instantáneas y conmutación SCR en su circuito de arranque. No habilita cualquier topología EMT ni un modelo térmico motor/semiconductor. |
| Series temporales de operación diaria/anual | No implementadas como módulo | Los perfiles estáticos de arranque P13C no son un estudio Daily/Yearly de la red. |
| Estabilidad dinámica de generadores y transferencia | No implementada por P12 | El equivalente de fuente y escenarios estáticos no resuelven sincronismo, AVR, gobernador ni interrupción transitoria del suministro. |
| Relés, CT/VT, lógica y selectividad integral | Fuera de P5-v1 | No están implementados el estudio integral de relés ni la selectividad energética, backup/cascading o ajustes automáticos verificados. |
| Ib de corte / Ik permanente IEC 60909 y deberes excluidos | No implementados/promovidos en P4-v1 | Aporte inicial Ik'' no cubre decaimiento near-generator ni ip/Ith con máquinas SC. |
| Arc flash IEEE 1584 | Diferido por solicitud del usuario | Lee educativo sigue disponible; no aporta conformidad IEEE 1584. |
| Comparación automática OpenDSS–pandapower | No implementada | Los motores se invocan explícitamente. Usar ambos en tareas distintas no es contrastar un mismo estudio entre ambos. |
| Selección automática de contingencias/deslastre y mínimos normativos universales | No implementada | El alcance, acciones, datos y criterios se declaran; no se deduce un mínimo universal de tensión. |
| Firma digital integrada | Mejora documental opcional | El ingeniero revisa, aprueba y firma el estudio. Integrar una firma digital al software no es requisito para verificar los cálculos. |

## Precisiones sobre documentos y estados

1. **P4-v1 vs P4-v1.1:** la matriz histórica de selección y el registro de madurez P4-v1 mantienen 2F-T fuera de su alcance original. La extensión P4-v1.1 ya ejecuta 2F-T con solver propio MCP y Z1/Z0 de pandapower. Su madurez y promoción normativa son diferentes; no debe omitirse ni confundirse con una falla nativa pandapower.
2. **P5:** `evaluar_cierre_p5` declara `READY_WITH_LIMITATIONS`; los cinco componentes están `VALIDATED_WITH_LIMITATIONS` por verificación Q1 en `obtener_matriz_validacion`. La evidencia de integración no concede conformidad normativa ni selectividad integral.
3. **P7/P8:** P7 mínimo y la Engineering Preview están cerrados como fases, pero sus contratos de componente conservan limitaciones históricas. La reconstrucción P7B no recupera automáticamente todos los datos estructurados ni convierte estudios guardados en vigentes.
4. **Arc flash:** tanto `estimar_arc_flash_lee` como el alias `calcular_arc_flash` calculan Lee simplificado. No hay cálculo IEEE 1584 implementado detrás del alias.
5. **Dinámica y perfiles:** las secuencias/perfiles estáticos no sustituyen la dinámica. MSL DOL común y SCR delta genérico están verificados en alcance. Ambos exigen su propio paquete; las etiquetas estáticas no los habilitan automáticamente.
6. **Conformidad:** P4 tiene revisión IEC con limitaciones; no se afirma conformidad integral ecuación por ecuación. El sistema conserva `professional_emission=false`.

## Herramientas principales por función

### 1. Modelo y datos

- **Crear y editar una red:** `crear_circuito`, `agregar_linea`, `agregar_carga`, `agregar_transformador`, `agregar_generador_respaldo`.
- **Construcción Rev.0 con datos pendientes:** `validar_construccion_rev0`, `construir_modelo_rev0`, `registrar_placeholder_modelo`, `obtener_placeholders_modelo`.
- **Datos profesionales de fuente y transformadores:** `definir_red_equivalente`, `agregar_transformador_profesional`, `obtener_datos_profesionales`.
- **Catálogo y asignación de cables:** `listar_conductores`, `obtener_conductor`, `aplicar_conductor`, `obtener_asignaciones_conductores`.
- **Secuencia cero y puesta a tierra:** `definir_secuencia_cero_fuente`, `definir_secuencia_cero_linea`, `definir_secuencia_cero_transformador`, `obtener_secuencia_cero`.
- **Auditoría y preparación del estudio:** `auditar_modelo`, `evaluar_preparacion_estudio`, `evaluar_preparacion_cortocircuito_3ph`.

### 2. Flujo de potencia y operación

- **Flujo de potencia principal:** `ejecutar_flujo_potencia`.
- **Flujo con motor alternativo:** `ejecutar_flujo_pandapower`.
- **Caída de tensión:** `analizar_caida_tension`.
- **Flujo detallado y cargabilidad:** `analizar_flujo_operacion`.
- **Estado de cierre:** `obtener_estado_cierre_modulos` (alcance, evidencia y gates finitos separados de preparación del proyecto).
- **Bancos y compensación reactiva:** `obtener_contrato_compensacion_reactiva`, `validar_compensacion_reactiva`, `ejecutar_compensacion_reactiva`.
- **Escenarios y contingencias N-1 declaradas:** `validar_escenarios_operativos`, `ejecutar_escenarios_operativos`, `simular_perdida_alimentador`.
- **Deslastre y fuentes alternativas:** `obtener_contrato_p12_escenarios_operativos`, `ejecutar_escenarios_operativos`.

### 3. Cortocircuito

- **Falla exploratoria FaultStudy:** `ejecutar_cortocircuito`.
- **Trifásico IEC 60909 MAX/MIN:** `evaluar_preparacion_cortocircuito_3ph`, `ejecutar_cortocircuito_iec60909_3ph`.
- **Bifásico fase-fase IEC 60909 MAX/MIN:** `ejecutar_cortocircuito_iec60909_2ph`.
- **Monofásico a tierra IEC 60909 MAX/MIN:** `ejecutar_cortocircuito_iec60909_1ph_ground`.
- **Bifásico a tierra MAX/MIN: extensión P4-v1.1:** `ejecutar_cortocircuito_iec60909_2ph_ground`.
- **Aporte de motores y generadores a falla 3F:** `clasificar_carga_cortocircuito_3ph`, `definir_motor_cortocircuito_3ph`, `definir_generador_cortocircuito_3ph`, `ejecutar_cortocircuito_iec60909_3ph`.
- **Pico ip y térmica equivalente Ith:** `ejecutar_cortocircuito_iec60909_3ph`, `ejecutar_cortocircuito_iec60909_2ph`.

### 4. Cables y protecciones

- **Ampacidad y relación Ib ≤ In ≤ Iz:** `definir_condiciones_ampacidad`, `evaluar_ampacidad`, `resolver_base_normativa_ampacidad`, `resolver_factor_normativo_ampacidad`.
- **Evidencia y aplicabilidad de ampacidad:** `definir_aplicabilidad_normativa_ampacidad`, `listar_datasets_numericos_ampacidad`, `evaluar_evidencia_normativa_ampacidad`.
- **Dispositivos, ajustes y curvas TCC:** `definir_dispositivo_proteccion_p5a`, `definir_ajustes_proteccion_p5a`, `registrar_dataset_curva_tcc_p5b`, `evaluar_curva_tcc_p5b`.
- **Capacidad de corte de la protección:** `evaluar_capacidad_corte_p5c`.
- **Soportabilidad térmica adiabática del conductor:** `evaluar_soportabilidad_termica_conductor_p5c`.
- **Tiempo final de despeje:** `evaluar_tiempo_despeje_p5d`.
- **Coordinación temporal entre dos protecciones:** `evaluar_coordinacion_temporal_p5e`.

### 5. Motores y arranque

- **Caída estática de tensión durante arranque:** `validar_arranque_motores`, `ejecutar_arranque_motores`.
- **Perfil de arranque por puntos declarados:** `validar_perfiles_arranque_motores`, `ejecutar_perfiles_arranque_motores`.
- **Secuencia de varios motores por estados declarados:** `validar_secuencias_arranque_motores`, `ejecutar_secuencias_arranque_motores`.
- **Dinámica MSL DOL verificada en alcance:** `obtener_contrato_dinamica_modelica`, `configurar_dinamica_modelica`, `validar_dinamica_modelica`, `ejecutar_dinamica_modelica`.
- **Dinámica SCR:** verificada en alcance MSL para una o dos máquinas delta y controles genéricos; estrella, más de dos motores y mezcla DOL/SCR excluidos; entradas antiguas retiradas.
- **Comparación del surrogate antiguo:** retirada; no genera nuevos resultados.
- **Contraste externo de dinámica con motor Modelica:** `contrastar_dinamica_con_modelica`.

### 6. Visualización, informes y uso local

- **Unifilar técnico y workspace:** `generar_diagrama_unifilar`, `configurar_workspace`, `regenerar_workspace`, `obtener_estado_workspace`.
- **Navegación, etiquetas y láminas de redes grandes:** `configurar_bus_unifilar`, `configurar_alimentador_unifilar`, `configurar_etiqueta_carga_unifilar`, `exportar_laminas_unifilar`.
- **Snapshot y reconstrucción:** `construir_snapshot_proyecto_p7a`, `verificar_snapshot_proyecto_p7a`, `reconstruir_snapshot_proyecto_p7b`.
- **Reporte técnico reproducible:** `exportar_reporte_tecnico_p7c`, `exportar_reporte_desde_archivo_p7c`.
- **Expedientes de proyecto, escenarios y arranque:** `generar_dossier_piloto_real`, `generar_dossier_escenarios_operativos`, `generar_dossier_arranque_motores`, `generar_dossier_dinamica_motores`, `generar_dossier_arranque_suave`.
- **Admisión de proyecto real y uso local:** `evaluar_admision_piloto_real`, `obtener_checklist_p8f5_datos_proyecto_real`, `obtener_contrato_p8f4_primer_uso`.
- **Arc flash simplificado de Lee:** `estimar_arc_flash_lee`, `calcular_arc_flash`.

## Fuentes y evidencia

- Inventario MCP íntegro: `Inventario-herramientas.json` (nombres, descripciones y esquemas de entrada).
- Respuestas reales de contratos: `Contratos-consultados.json`.
- Fecha, versión y llamadas: `Evidencia-consulta.json`.
- Código: `mcp_electrico/engine_selection.py`, `validation_status.py`, `iec60909_maturity.py`, `iec60909_two_phase_ground_suite.py`, `motor_starting_static.py`, `motor_dynamics.py`, `motor_soft_starting.py`, `operating_scenarios.py`, `p5_completion.py` y `visual_sheets.py`.
- Alcances documentados: `docs/P4V11_2FT_REENTRY.md`, `docs/P13F_MOTOR_DYNAMICS.md`, `docs/P13G_SOFT_STARTING.md`, `docs/ROADMAP_PROFESIONAL.md` y `docs/ROADMAP_VISUAL.md`.

Esta matriz amplía el catálogo histórico de selección sin modificar sus contratos ni el código de cálculo. Debe revisarse cuando cambie el alcance implementado.
