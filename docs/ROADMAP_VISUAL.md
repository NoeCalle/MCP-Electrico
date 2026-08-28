# Roadmap visual transversal — MCP Eléctrico

## Objetivo

Mantener la evolución visual del proyecto alineada con la evolución técnica. El workspace y el unifilar no son decoración: deben permitir comprender el modelo, inspeccionar resultados, identificar condiciones anormales y conservar trazabilidad entre elemento eléctrico, estudio y revisión del modelo.

Este roadmap no reemplaza `docs/ROADMAP_PROFESIONAL.md`. Funciona como eje transversal: cuando una fase P2–P7 introduce un nuevo objeto o estudio, debe evaluarse también su representación visual.

## Estado base ya conseguido

La línea visual actual ya incluye:

- unifilar técnico SVG v2 con diferenciación entre barra física y bus lógico;
- simbología para fuente, barras, transformador, protecciones, ATS, UPS, motores, cargas y grupo electrógeno;
- workspace HTML persistente y autocontenido;
- identificadores estables por elemento;
- selección desde SVG, tablas y selector lateral;
- inspector técnico read-only;
- sincronización de selección entre estudio e inspector;
- pestañas de flujo y caída de tensión;
- overlays visuales sobre el unifilar para flujo/cargabilidad y caída de tensión;
- exportación SVG e impresión/PDF;
- validación de JavaScript en CI mediante `node --check`;
- V4 experimental de cortocircuito con 3F, 2F y 1F-T MAX/MIN versionados, barras de falla y madurez visible.

## Principios visuales no negociables

1. El navegador no realiza cálculos eléctricos; presenta resultados estructurados generados por MCP Eléctrico.
2. Un resultado visual debe declarar su `model_revision` y no mostrarse como vigente si el modelo cambió.
3. Los IDs del modelo son canónicos. No se crea un segundo sistema de identidad para tablas, overlays o nuevos motores.
4. El unifilar representa ingeniería, no la topología interna literal del solver.
5. No se inventan equipos, protecciones, ratings, impedancias ni estados para completar un dibujo.
6. Los datos visuales provenientes de catálogo, usuario o cálculo deben conservar su procedencia cuando sea técnicamente relevante.
7. Cuando existan varios motores, cada estudio debe mostrar claramente qué motor produjo el resultado; nunca se mezclan resultados de motores distintos dentro de una misma vista sin una función específica para ello.
8. La madurez del módulo (`EXPERIMENTAL`, `VALIDATED_WITH_LIMITATIONS`, etc.) debe ser visible cuando el usuario consulte un estudio que no sea plenamente validado.
9. Las vistas de ingeniería deben seguir siendo legibles en SVG, HTML y salida impresa.
10. La incorporación de una nueva feature numérica no se considera visualmente terminada hasta decidir si requiere inspector, tabla, overlay, símbolo o salida de reporte.

## V1 — Base visual existente

**Estado: IMPLEMENTADA.**

Incluye el unifilar técnico v2, workspace persistente, inspector, selección sincronizada y las primeras vistas de estudios.

Pendientes de consolidación:

- eliminar deuda técnica restante de bindings/IDs que todavía se resuelva en runtime;
- pruebas visuales/regresiones estructurales más fuertes además del chequeo sintáctico JavaScript;
- mejorar manejo de redes grandes sin sacrificar legibilidad.

## V2 — Acompañamiento visual de P2: datos profesionales

**Estado: COMPLETA CON LIMITACIONES (V2/P2 v1).**

El workspace implementa la trazabilidad visual necesaria para cerrar P2 v1. El inspector y la tabla distinguen información profesional estructurada de una mera anotación visual.

### Transformadores

Implementado:

- kVA/MVA nominal;
- tensiones nominales;
- grupo vectorial;
- `%Z`;
- X/R cuando existe;
- taps y posición vigente;
- pérdidas e I0 cuando forman parte de la ficha P2;
- procedencia de datos;
- estado de suficiencia de proyección pandapower y secuencia cero.

El símbolo del transformador puede mantener resumida la relación de tensión/grupo; el detalle completo permanece en el inspector.

### Fuente / red equivalente

Implementado en el inspector de la fuente:

- tensión nominal/modelo;
- Scc máxima y mínima cuando existen;
- X/R máximo/mínimo;
- escenario activo;
- estado de secuencia cero;
- procedencia de los datos.

### Conductores BT/MT

El inspector del alimentador ya distingue una asignación de biblioteca trazable de un simple texto visual y presenta:

- familia y fabricante;
- nivel/clase disponible en catálogo;
- sección y pantalla cuando corresponda;
- Rdc20 cuando existe;
- R1/X1 aplicados y R1/X1 activos del modelo;
- ampacidad de catálogo;
- condición/clave de instalación asociada;
- procedencia.

Se mantiene visible la advertencia de que la ampacidad publicada **no es `Iz` normativo P3**.

### Limitación V2 deliberada

El readiness específico (`READY_DATA`, `MISSING_DATA`, `ENGINE_NOT_READY`) se expone ya por tools MCP y por el eje E. Su representación gráfica se incorpora progresivamente en las vistas específicas V3–V6 de cada estudio, donde existe contexto inequívoco para interpretarlo; V2 no inventa un “estudio activo” en el workspace.

## V3 — Acompañamiento visual de P3: ampacidad

**Estado: COMPLETA CON LIMITACIONES (V3/P3-v1).**

Hito conservado: **BASE NORMATIVA P3C10** visible y trazable en V3; el cierre P3C13 no elimina esa evidencia histórica.

La vista ya incorpora una pestaña específica de ampacidad que consume exclusivamente resultados preparados por Python y permite distinguir:

- perfil normativo asociado cuando existe;
- método de instalación P3A;
- estado del routing normativo (`BASE_CONDITIONS_IDENTIFIED`, `REQUIREMENTS_IDENTIFIED`, etc.);
- `Ib` corriente de diseño o corriente de flujo aceptada expresamente como Ib;
- `In` de protección declarado;
- `Iz_base` trazable;
- origen de `Iz_base` como `CATÁLOGO P2`, `PRIMARIA`, `SECUNDARIA` o `INCOMPLETA`;
- **Tabla / dataset base** cuando existe base normativa P3B;
- producto de factores `∏k`;
- `Iz` calculada;
- estado `CUMPLE` / `NO_CUMPLE` / `DATOS_INSUFICIENTES`;
- calidad de evidencia de factores resumida como `PRIMARIA`, `SECUNDARIA`, `MANUAL`, `BASE`, `MIXTA` o `INCOMPLETA`;
- aviso visible de madurez `VALIDATED_WITH_LIMITATIONS` y límites del alcance P3-v1;
- separación visual entre cálculo técnicamente ejecutable y evidencia normativa profesional suficiente.

La primera base normativa primaria P3C10 permite que V3 muestre de forma explícita, sin recalcular, la procedencia de `Iz_base=229 A` para el caso exacto Método C / Cu / XLPE-EPR / 3 conductores cargados / 70 mm² mediante `PERU_CNE_UTIL_2006_TABLE_2_COL23_C_XLPE_3C_CU_70MM2_PRIMARY_V1`. La ampacidad de catálogo P2 permanece separada y no se presenta como la misma magnitud.

La clasificación de evidencia se calcula en Python a partir de la procedencia de factores y datasets. **El JavaScript no decide si una evidencia es primaria o secundaria.** Solo presenta la etiqueta ya estructurada.

Si no existe routing P3A, la vista identifica el cálculo como foundation manual y conserva la referencia normativa de la ficha P3 cuando está disponible.

La selección de una fila sincroniza el alimentador con el inspector. **El JavaScript de V3 no calcula** `Ib`, `In`, factores, `Iz`, tablas, routing ni clasificación normativa: únicamente presenta datos ya estructurados por Python y gestiona navegación.

### Vínculo con el gate P3

El gate formal P3 ya existe en backend y distingue `phase` de `model`. El cierre P3-v1 mantiene visible la evidencia exacta y no convierte cobertura limitada en cobertura exhaustiva.

Trabajo visual incremental de V3:

- mostrar de forma compacta referencia de fuente/página y nivel de evidencia sin saturar la tabla principal;
- mostrar motivos de `MISSING_DATA`, revisión manual o bloqueo de evidencia de manera legible;
- decidir overlay del unifilar para `NO_CUMPLE` sin convertirlo en sustituto del panel de estudio;
- ampliar pruebas visuales conforme crezca cobertura `PRIMARY_VERIFIED`;
- conservar impresión/PDF legible y trazable.

## V4 — Acompañamiento visual de P4: cortocircuito IEC 60909

**Estado: EN DESARROLLO — P4C11A 3F DONE + P4C11B 2F DONE + P4C11C 1F-T DONE.**

La vista V4 reutiliza el mismo workspace/unifilar/inspector de V3; no crea una aplicación paralela ni realiza cálculos IEC 60909 en JavaScript.

### P4C11A — 3F

Implementado:

- tool pública `ejecutar_cortocircuito_iec60909_3ph`;
- snapshot versionado `iec60909_3ph`;
- escenarios MAX/MIN;
- `Ik''`, `Sk''`, `ip`, `Ith`, Rk y Xk según datos disponibles;
- topología, `tk_s` y κ efectivos;
- motor y versión;
- edición objetivo y estado de conformidad;
- madurez `EXPERIMENTAL_P4`;
- `professional_emission=false`;
- barra de falla resaltada en el unifilar;
- fail-closed visual si MIN no puede calcularse.

### P4C11B — 2F

Implementado:

- tool pública `ejecutar_cortocircuito_iec60909_2ph`;
- snapshot versionado `iec60909_2ph`;
- escenarios MAX/MIN;
- `Ik''`, `ip`, `Ith`, Rk y Xk según datos disponibles;
- política `Z2 = Z1` visible con alcance simétrico pasivo y `universal_assumption=false`;
- `Sk''` 2F no normalizado se muestra como ausencia de dato; el navegador no lo deriva;
- coexistencia con los demás estudios de falla sin sobrescribir snapshots;
- overlay de todas las barras de falla vigentes.

### P4C11C — 1F-T

Implementado:

- tool MCP pública `ejecutar_cortocircuito_iec60909_1ph_ground`;
- snapshot versionado `iec60909_1ph_ground`;
- escenarios MAX/MIN;
- `Ik''`, Rk/Xk y Rk0/Xk0;
- política `Z2 = Z1` visible con alcance simétrico pasivo y `universal_assumption=false`;
- evidencia de secuencia cero de fuente, líneas y transformadores preparada en Python;
- contador visible de líneas con Z0/C0 y transformadores con Z0/neutro proyectados;
- `Sk''`, `ip` e `Ith` se muestran como ausencia de dato contractual; JavaScript no los deriva;
- coexistencia **3F + 2F + 1F-T** en la misma pestaña y revisión de modelo;
- overlay de todas las barras de falla vigentes e integración con el inspector existente;
- ejemplo reproducible `examples/workspace_p4_1ph_ground.py`;
- CI dedicado genera y valida artefactos 3F/2F/1F-T y verifica sintaxis JavaScript.

La pestaña **Cortocircuito** muestra únicamente estudios vigentes para la revisión actual. Si cambia el modelo, la infraestructura de `workspace_state` invalida los resultados anteriores.

P4C11A, P4C11B y P4C11C están cerrados como subhitos. **P4C11 global permanece `PENDING`** hasta fijar el alcance final que efectivamente cierre P4-v1. P4C08 debe decidir si 2F-T se implementa mediante una estrategia numérica validable o queda formalmente fuera del alcance de esa versión; no se forzará una representación visual mientras esa decisión no exista.

## V5 — Acompañamiento visual de P5: protección y TCC

Esta fase requiere una ampliación visual importante:

- símbolos/estado de interruptores, relés y fusibles vinculados a objetos reales;
- inspector de protección con In, Icu/Ics/Icw y ajustes Ir/Isd/Ii cuando correspondan;
- panel TCC dedicado;
- curvas de protección y daño térmico/conductor cuando haya información suficiente;
- márgenes de coordinación y tiempos de despeje;
- resultado de verificación `I²t <= k²S²`;
- advertencia visible si faltan curvas comerciales o datos del fabricante.

La TCC será una vista de estudio, no una deformación del unifilar.

## V6 — Acompañamiento visual de P6: Arc Flash

La vista IEEE 1584 deberá mostrar de forma diferenciada:

- barra/equipo evaluado;
- configuración de electrodos;
- gap;
- working distance;
- Iarc e Iarc_min;
- tiempo de despeje vinculado a protección;
- energía incidente;
- arc-flash boundary;
- escenario dominante;
- estado de validación.

El unifilar podrá usar badges o marcadores de riesgo, pero la información necesaria para una etiqueta deberá mantenerse en una vista/artefacto específico.

## V7 — Acompañamiento visual de P7: expediente y reporte

El workspace y los SVG deben poder alimentar un reporte reproducible sin redibujar manualmente resultados.

Objetivos:

- láminas vectoriales aptas para PDF;
- tablas con unidades y procedencia;
- identificación de revisión/model hash;
- estado de validación de cada estudio;
- warnings/limitaciones visibles;
- selección consistente de vistas para anexos;
- estilo de impresión limpio sin controles interactivos.

## Regla para pandapower

P1.5 no crea por ahora una segunda interfaz visual. Los resultados pandapower se registran como estudios independientes y deben identificar explícitamente:

- `engine = pandapower`;
- versión;
- estado de madurez;
- alcance/compatibilidad.

No habrá overlay comparativo con OpenDSS ni cross-check visual mientras esa función no exista formalmente.

## Criterio de aceptación visual por PR

Cuando un PR modifica el workspace/unifilar o añade una nueva vista, debe comprobar según aplique:

- generación HTML/SVG exitosa;
- IDs estables y selección funcional;
- resultados ligados a la revisión vigente;
- JavaScript válido;
- ausencia de cálculos eléctricos en navegador;
- representación explícita de datos faltantes, no inferidos;
- procedencia/evidencia visible cuando afecte la interpretación del estudio;
- salida imprimible razonable;
- regresión de vistas ya existentes.

A futuro se añadirá validación visual automatizada por screenshots/diffs para componentes críticos, además de las comprobaciones estructurales actuales.
