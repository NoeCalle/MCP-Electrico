# P3 — Ampacidad foundation

## Estado

**UNDER_VALIDATION.**

P3 incorpora el contrato de cálculo y trazabilidad para verificar:

```text
Ib <= In <= Iz
```

pero **no** declara todavía una implementación automática completa de IEC 60364-5-52 ni del CNE–Utilización. La foundation separa correctamente los datos y evita convertir una ampacidad de catálogo en `Iz` normativo sin justificación.

P3A añade un **router normativo de aplicabilidad**: identifica qué tabla base y qué ejes de corrección resultan aplicables dentro del alcance modelado.

P3B añade la infraestructura de **datasets numéricos versionados**, con revisiones primarias exactas ya disponibles para un subconjunto de Tabla 5C y para el primer caso de `Iz_base` Tabla 2. La disponibilidad de esos subconjuntos no equivale a cobertura normativa completa.

## Referencias registradas

El registro P3 incluye, como referencias versionadas:

- `IEC_60364_5_52_2009_A1_2024`: IEC 60364-5-52:2009+AMD1:2024, Ed. 3.1, publicada el 2024-11-22;
- `PERU_CNE_UTILIZACION_2006`: Código Nacional de Electricidad – Utilización, aprobado por R.M. N.° 0037-2006-MEM.

Registrar una norma **no significa** que sus tablas estén implementadas o verificadas. Cada dataset debe declarar su procedencia y política de uso.

La copia oficial de referencia del CNE–Utilización 2006 está fijada por el proyecto con:

```text
source_id = MINEM_CNE_UTIL_2006_OFFICIAL_PDF
pin_status = PINNED
expected_sha256 = 2b3cbd457c519bf9d9aa2cf2754c72b6e531708e45ea2fdf91f839b1acccfd64
```

Esto completa P3C08. El pin identifica el archivo de referencia byte a byte, pero no valida por sí solo ninguna tabla.

## P3A — perfiles normativos

Se registran dos perfiles separados:

- `PERU_CNE_UTIL_2006_030_004`: router de aplicabilidad para la Regla 030-004 del CNE–Utilización 2006;
- `IEC_60364_5_52_2009_A1_2024`: `REFERENCE_ONLY`; la edición 3.1 está registrada, pero sus tablas numéricas no están cargadas.

El perfil CNE modela actualmente:

- métodos E/F/G → Tabla 1;
- métodos A1/A2/B1/B2/C/D → Tabla 2;
- temperatura → Regla 030-004(8) / Tabla 5A;
- resistividad térmica del suelo para el alcance modelado de método D en ductos enterrados → Regla 030-004(9) / Tabla 5B;
- agrupamiento A1/A2/B1/B2/C → Tabla 5C dentro del alcance soportado;
- agrupamiento método D enterrado → **Tabla 5D**, con disposición/separación todavía bajo revisión manual hasta cargar su dataset específico;
- métodos E/F/G → rama 5C/5E según disposición física, todavía `MANUAL_REVIEW_REQUIRED` cuando la rama no es inequívoca;
- transición subterránea → visible dentro del alcance de 030-004(13);
- excepción 030-004(14) siempre como `MANUAL_REVIEW_REQUIRED`.

P3A **no generaliza** 030-004(13) a cualquier cambio de instalación.

Detalle completo: `docs/P3A_PERFILES_NORMATIVOS.md`.

## P3B — datasets numéricos

P3B introduce un registro estructurado de datasets con:

- `source_type`;
- `verification_status`;
- publisher/referencia/URL o fuente primaria pinneada;
- alcance exacto;
- política de interpolación/extrapolación;
- `professional_emission`.

La reproducción secundaria histórica permanece:

`PERU_CNE_UTIL_2006_TABLE_5C_ITEM1_SECONDARY_V1`

Por política conserva:

```text
verification_status = PENDING_PRIMARY_VERIFICATION
professional_emission = false
automatic_normative_lookup = false
```

El valor secundario no se devuelve por defecto. Requiere opt-in explícito y aun así continúa marcado como no apto para emisión.

P3C09 añadió una revisión primaria independiente, limitada a las celdas realmente verificadas de Tabla 5C:

`PERU_CNE_UTIL_2006_TABLE_5C_ITEM1_PRIMARY_V1`

con 2→0.80, 3→0.70 y 12→0.45.

P3C10 añade la primera base normativa primaria real:

`PERU_CNE_UTIL_2006_TABLE_2_COL23_C_XLPE_3C_CU_70MM2_PRIMARY_V1`

Consulta exacta:

```text
Método C
Cu
XLPE/EPR — 90 °C
3 conductores cargados
70 mm2
Tabla 2, Col. 23
Iz_base = 229 A
```

La Tabla 3 confirma el routing hacia Tabla 2 Col. 23. El dataset contiene una sola fila `exact_rows_v1`; cualquier consulta distinta devuelve `VALUE_NOT_TABULATED`. P3B no interpola, extrapola ni usa vecino más cercano.

Detalle: `docs/P3B_DATASETS_NUMERICOS.md` y `docs/P3C10_BASE_AMPACITY_STRATEGY.md`.

## Variables

### Ib — corriente de diseño

P3 acepta dos modos:

1. `EXPLICIT_DESIGN_CURRENT`: el usuario aporta `Ib` y una referencia/metodología;
2. `FLOW_CURRENT_EXPLICITLY_ACCEPTED_AS_IB`: se usa la corriente máxima resultante del flujo OpenDSS **solo después de una aceptación explícita** de que ese escenario representa la corriente de diseño.

El sistema nunca convierte automáticamente una corriente de flujo en `Ib`.

### In — corriente nominal/ajuste de protección

`In` se declara expresamente junto con su referencia. El campo visual histórico `corriente_nominal_a` del alimentador **no se interpreta como In**, porque también ha sido utilizado para representar ampacidad/rating de conductor en vistas anteriores.

### Iz base

P3 mantiene dos fuentes conceptualmente distintas:

1. **ampacidad de catálogo P2**, trazable al producto/fabricante y condición publicada;
2. **base normativa P3**, cuando existe una coincidencia exacta en un dataset `base_ampacity` validado.

La base normativa, cuando existe, entra mediante `ampacity_base_binding.py`, conserva dataset, tabla, query, perfil, referencia normativa y procedencia, y se revalida contra el catálogo activo antes de configurar y evaluar.

Para el caso P3C10 actualmente validado:

```text
ampacidad catálogo P2 = 296 A
Iz_base normativa CNE = 229 A
```

El sistema conserva ambas. El valor P2 **no se transforma** en 229 A ni se reemplaza silenciosamente; la base normativa es una fuente adicional y explícita para el cálculo P3.

### Factores de corrección

Cuando se suministran factores explícitos:

```text
Iz = Iz_base * product(k_i)
```

cada factor debe contener:

- identificador;
- valor;
- referencia;
- `axis` cuando existe routing P3A vinculado;
- tabla/cláusula opcional;
- condición opcional.

Además se exige `referencia_condiciones_instalacion`, que documenta por qué los factores elegidos son compatibles con la condición base de la ampacidad utilizada.

Si no se aplican factores, el usuario debe confirmar expresamente que las condiciones reales coinciden con las condiciones base publicadas y documentar esa comprobación. P3 no asume silenciosamente `product(k_i)=1`.

Cuando P3A identifica un eje requerido, ya no se permite confirmar condiciones base ni omitir el vínculo del factor con ese eje.

## Resultado

La evaluación devuelve:

- `CUMPLE`;
- `NO_CUMPLE`;
- `DATOS_INSUFICIENTES`.

Y conserva por separado:

- `Ib`;
- `In`;
- `Iz_base`;
- origen y evidencia de `Iz_base`;
- referencia de catálogo P2 en paralelo;
- factor total;
- `Iz`;
- chequeo `Ib <= In`;
- chequeo `In <= Iz`;
- referencias de Ib/In/base/factores/condiciones;
- norma registrada;
- routing P3A vinculado cuando existe;
- madurez `UNDER_VALIDATION`.

## Seguridad de estado

Un perfil P3 se invalida si la asignación P2 deja de coincidir con la ficha sobre la que fue creado. Se detectan al menos:

- cambio de conductor;
- cambio de condición de instalación;
- cambio de ampacidad de catálogo P2.

Cuando existe `base_normativa`, también se revalida el dataset exacto al evaluar. Si cambia el valor, query, tabla, perfil o procedencia del dataset, la evaluación queda en `DATOS_INSUFICIENTES`.

Crear un circuito nuevo también limpia los perfiles y routings P3/P3A.

Si el routing normativo se redefine después de crear la ficha `Ib/In/Iz`, la evaluación y el readiness vuelven a comprobar norma, ejes requeridos y revisiones manuales.

P3B añade otra regla: el lookup numérico debe usar las mismas condiciones y dimensiones declaradas por el escenario. Una discrepancia de routing específico devuelve `ROUTE_MISMATCH`; una consulta genérica fuera de las dimensiones exactas verificadas no se resuelve.

## Readiness y matriz E

La matriz de motores declara ampacidad como:

- backend preferente: `mcp`;
- implementación: disponible en foundation;
- madurez: `UNDER_VALIDATION`;
- emisión profesional automática: no habilitada.

`evaluar_preparacion_estudio("ampacidad")` comprueba un contrato específico P3 y no exige indiscriminadamente todos los datos de flujo/cortocircuito.

Cuando existe routing P3A, el readiness bloquea:

- parámetros normativos faltantes;
- perfil `REFERENCE_ONLY` sin dataset aplicable;
- revisión manual pendiente;
- mezcla entre referencia CNE e IEC;
- eje requerido sin factor explícito asociado;
- confirmación de condiciones base cuando el router identifica correcciones.

La presencia de un dataset P3B secundario **no cambia ese gate profesional**. Del mismo modo, un dataset primario puntual no eleva por sí solo la madurez global P3.

## Workspace V3

La vista Ampacidad muestra resultados ya calculados por Python:

- Ib;
- In;
- Iz base;
- origen de Iz base;
- **Tabla / dataset base** cuando existe base normativa;
- producto de factores;
- Iz;
- estado;
- perfil/método/routing P3A cuando existe;
- calidad de evidencia normativa preparada por Python.

El navegador sigue sin calcular corrientes, factores, criterios, tablas ni clasificación de evidencia.

V3 puede mostrar la nueva base primaria P3C10 como `PRIMARIA` y exponer `Tabla 2 · PERU_CNE_UTIL_2006_TABLE_2_COL23_C_XLPE_3C_CU_70MM2_PRIMARY_V1` porque esa información ya llega estructurada desde Python. JavaScript no hace lookup.

## Casos patrón y benchmarks

### P3A

Los casos de routing están separados del algoritmo en:

`mcp_electrico/data/ampacity_p3a_reference_cases.json`

Prueban **aplicabilidad**, no valores numéricos.

### P3B

Los casos numéricos históricos de infraestructura están en:

`mcp_electrico/data/ampacity_p3b_benchmark_cases.json`

`examples/run_benchmarks_p3b.py` genera `benchmark_p3b.json` y conserva explícitamente:

```text
evidence_level = SECONDARY
professional_emission = false
```

Así un benchmark verde de infraestructura no puede confundirse con validación normativa primaria. Los benchmarks independientes necesarios para P3C12 se gestionan mediante evidencia separada.

## Gate formal de salida

`evaluar_cierre_p3()` implementa los criterios `P3C01`–`P3C13` y separa el estado de la fase del estado de un modelo concreto.

Estado tras P3C10:

- `P3C01`–`P3C10`: `DONE`;
- `P3C11`–`P3C13`: pendientes;
- `phase_status = NOT_READY`;
- `ready_for_next_phase = false`;
- `professional_emission = false`.

P4 solo aparece como siguiente fase cuando todos los criterios estén completos.

## Qué falta para cerrar P3

P3/P3A/P3B **no cierran todavía P3**. Permanecen pendientes:

1. completar la cobertura primaria 5A/5B/5C/5D/5E (`P3C11`);
2. construir benchmarks independientes primarios por familia (`P3C12`);
3. mantener BT/MT y ámbitos normativos claramente separados;
4. ampliar Tablas 1/2 de forma incremental cuando nuevos casos lo requieran, siempre mediante filas exactas verificadas;
5. validar casos límite y política de valores no tabulados;
6. elevar la madurez solo si la evidencia lo permite (`P3C13`).

Hasta ese cierre, cualquier resultado P3 debe conservar visible `UNDER_VALIDATION`.