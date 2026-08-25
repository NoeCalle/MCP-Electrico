# P3 — Ampacidad foundation

## Estado

**UNDER_VALIDATION.**

P3 incorpora el contrato de cálculo y trazabilidad para verificar:

```text
Ib <= In <= Iz
```

pero **no** declara todavía una implementación automática completa de IEC 60364-5-52 ni del CNE–Utilización. La foundation separa correctamente los datos y evita convertir una ampacidad de catálogo en `Iz` normativo sin justificación.

P3A añade un **router normativo de aplicabilidad**: identifica qué tabla base y qué ejes de corrección resultan aplicables dentro del alcance modelado.

P3B añade la infraestructura de **datasets numéricos versionados**, pero distingue estrictamente entre un valor disponible para desarrollo y un valor verificado que pueda sustentar emisión profesional.

## Referencias registradas

El registro P3 incluye, como referencias versionadas:

- `IEC_60364_5_52_2009_A1_2024`: IEC 60364-5-52:2009+AMD1:2024, Ed. 3.1, publicada el 2024-11-22;
- `PERU_CNE_UTILIZACION_2006`: Código Nacional de Electricidad – Utilización, aprobado por R.M. N.° 0037-2006-MEM.

Registrar una norma **no significa** que sus tablas estén implementadas o verificadas. Cada dataset debe declarar su procedencia y política de uso.

La copia oficial de referencia del CNE–Utilización 2006 ya está fijada por el proyecto con:

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
- publisher/referencia/URL;
- alcance exacto;
- política de interpolación/extrapolación;
- `professional_emission`.

El primer dataset es:

`PERU_CNE_UTIL_2006_TABLE_5C_ITEM1_SECONDARY_V1`

Corresponde a una reproducción secundaria de una fila de Tabla 5C y se usa **solo para desarrollo/benchmark de la infraestructura**.

Por política:

```text
verification_status = PENDING_PRIMARY_VERIFICATION
professional_emission = false
automatic_normative_lookup = false
```

El valor secundario no se devuelve por defecto. Requiere un opt-in explícito y aun así continúa marcado como no apto para emisión.

P3B tampoco interpola ni extrapola valores no tabulados.

El siguiente paso de evidencia es P3C09: contrastar un subconjunto pequeño contra la copia oficial pinneada y crear una revisión nueva `PRIMARY_VERIFIED` mediante PR + CI. La revisión secundaria existente no se transforma silenciosamente.

Detalle: `docs/P3B_DATASETS_NUMERICOS.md`.

## Variables

### Ib — corriente de diseño

P3 acepta dos modos:

1. `EXPLICIT_DESIGN_CURRENT`: el usuario aporta `Ib` y una referencia/metodología;
2. `FLOW_CURRENT_EXPLICITLY_ACCEPTED_AS_IB`: se usa la corriente máxima resultante del flujo OpenDSS **solo después de una aceptación explícita** de que ese escenario representa la corriente de diseño.

El sistema nunca convierte automáticamente una corriente de flujo en `Ib`.

### In — corriente nominal/ajuste de protección

`In` se declara expresamente junto con su referencia. El campo visual histórico `corriente_nominal_a` del alimentador **no se interpreta como In**, porque también ha sido utilizado para representar ampacidad/rating de conductor en vistas anteriores.

### Iz base

La foundation usa como punto de partida la ampacidad trazable de una asignación P2 de conductor y conserva:

- producto/código;
- condición de instalación publicada;
- fuente del fabricante;
- ampacidad base.

Ese valor sigue identificado como **ampacidad base de catálogo**, no como `Iz` normativo final.

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
- cambio de ampacidad base.

Crear un circuito nuevo también limpia los perfiles y routings P3/P3A.

Si el routing normativo se redefine después de crear la ficha `Ib/In/Iz`, la evaluación y el readiness vuelven a comprobar norma, ejes requeridos y revisiones manuales.

P3B añade otra regla: el lookup numérico debe usar **la misma cantidad de circuitos y disposición** declaradas por P3A. Una discrepancia devuelve `ROUTE_MISMATCH`.

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

La presencia de un dataset P3B secundario **no cambia ese gate profesional**.

## Workspace V3

La vista Ampacidad muestra resultados ya calculados por Python:

- Ib;
- In;
- Iz base;
- producto de factores;
- Iz;
- estado;
- perfil/método/routing P3A cuando existe;
- calidad de evidencia normativa preparada por Python.

El navegador sigue sin calcular corrientes, factores, criterios ni clasificación de evidencia.

El cierre de P3C08 por sí solo no cambia visualmente un factor secundario a primario. V3 solo mostrará evidencia primaria cuando exista un dataset `PRIMARY_VERIFIED` real y esa procedencia llegue al cálculo.

## Casos patrón y benchmarks

### P3A

Los casos de routing están separados del algoritmo en:

`mcp_electrico/data/ampacity_p3a_reference_cases.json`

Prueban **aplicabilidad**, no valores numéricos.

### P3B

Los casos numéricos de infraestructura están en:

`mcp_electrico/data/ampacity_p3b_benchmark_cases.json`

`examples/run_benchmarks_p3b.py` genera `benchmark_p3b.json` y CI exige explícitamente:

```text
evidence_level = SECONDARY
professional_emission = false
```

Así un benchmark verde no puede confundirse con validación normativa primaria.

## Gate formal de salida

`evaluar_cierre_p3()` ya implementa los criterios `P3C01`–`P3C13` y separa el estado de la fase del estado de un modelo concreto.

A partir del pin de fuente:

- `P3C01`–`P3C08`: `DONE`;
- `P3C09`–`P3C13`: pendientes.

P4 solo aparece como siguiente fase cuando todos los criterios estén completos.

## Qué falta para cerrar P3

P3/P3A/P3B **no cierran todavía P3**. Permanecen pendientes:

1. crear el primer dataset `PRIMARY_VERIFIED` contra la copia CNE pinneada (`P3C09`);
2. validar la estrategia normativa de `Iz_base` mediante Tablas 1/2 o equivalente formalmente validado (`P3C10`);
3. completar la cobertura primaria 5A/5B/5C/5D/5E (`P3C11`);
4. construir benchmarks independientes primarios por familia (`P3C12`);
5. mantener BT/MT y ámbitos normativos claramente separados;
6. validar casos límite y política de valores no tabulados;
7. elevar la madurez solo si la evidencia lo permite (`P3C13`).

Hasta ese cierre, cualquier resultado P3 debe conservar visible `UNDER_VALIDATION`.
