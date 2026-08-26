# P3 — Ampacidad normativa

## Estado

**VALIDATED_WITH_LIMITATIONS — P3-v1 CERRADA.**

P3 implementa el contrato de cálculo y trazabilidad:

```text
Ib <= In <= Iz
Iz = Iz_base * product(k_i)
```

para el perfil peruano `PERU_CNE_UTIL_2006_030_004`, con fuente oficial pinneada, datasets normativos versionados, routing P3A, evidencia P3B y benchmarks primarios independientes. El cierre P3-v1 no significa que todo el CNE esté transcrito ni que cualquier combinación física pueda resolverse automáticamente.

El gate formal `evaluar_cierre_p3()` tiene `P3C01`–`P3C13 = DONE` y devuelve `READY_WITH_LIMITATIONS`; P4 IEC 60909 es la siguiente fase principal. `professional_emission = false` permanece como política global: la madurez del módulo no sustituye QA, datos suficientes ni revisión del ingeniero.

## Referencias registradas

- `PERU_CNE_UTILIZACION_2006`: Código Nacional de Electricidad – Utilización, R.M. N.° 0037-2006-MEM.
- `IEC_60364_5_52_2009_A1_2024`: registrada como `REFERENCE_ONLY`; no se mezcla con el perfil CNE.

Fuente oficial CNE pinneada:

```text
source_id = MINEM_CNE_UTIL_2006_OFFICIAL_PDF
pin_status = PINNED
expected_sha256 = 2b3cbd457c519bf9d9aa2cf2754c72b6e531708e45ea2fdf91f839b1acccfd64
```

El pin identifica exactamente el archivo de referencia. La validación de valores se realiza aparte mediante datasets `PRIMARY_VERIFIED` y benchmarks independientes.

## P3A — routing normativo

El perfil `PERU_CNE_UTIL_2006_030_004` enruta, dentro de su alcance:

- métodos E/F/G → Tabla 1;
- métodos A1/A2/B1/B2/C/D → Tabla 2;
- temperatura → Tabla 5A;
- resistividad térmica de suelo para D en ducto enterrado → Tabla 5B;
- agrupamiento A1/A2/B1/B2/C → Tabla 5C;
- agrupamiento D enterrado → **Tabla 5D**;
- métodos E/F/G → Tabla 5C/5E según disposición;
- 030-004(13) solo en la transición subterránea modelada;
- 030-004(14) permanece manual.

Los parámetros faltantes o las combinaciones fuera de alcance no se completan por inferencia. Detalle: `docs/P3A_PERFILES_NORMATIVOS.md`.

## P3B — datasets y evidencia

Los datasets declaran como mínimo:

- fuente y norma;
- `verification_status`;
- alcance exacto;
- dimensiones de consulta;
- política de interpolación/extrapolación;
- política de uso profesional;
- SHA-256 de fuente cuando corresponde.

El dataset secundario histórico se conserva para regresión de infraestructura:

`PERU_CNE_UTIL_2006_TABLE_5C_ITEM1_SECONDARY_V1`

con:

```text
verification_status = PENDING_PRIMARY_VERIFICATION
professional_emission = false
automatic_normative_lookup = false
```

Requiere opt-in explícito y nunca se presenta como evidencia primaria.

Los datasets primarios P3-v1 cubren las familias necesarias para el gate: estrategia de `Iz_base`, 5A, 5B, 5C, 5D y 5E. Los lookups normativos son exactos: no hay interpolación, extrapolación ni vecino más cercano.

Detalle: `docs/P3B_DATASETS_NUMERICOS.md` y `docs/P3B_EVIDENCIA_PRIMARIA.md`.

## Ib — corriente de diseño

P3 acepta:

1. `EXPLICIT_DESIGN_CURRENT`: Ib aportada explícitamente con referencia/metodología;
2. `FLOW_CURRENT_EXPLICITLY_ACCEPTED_AS_IB`: corriente de flujo usada como Ib solo tras aceptación explícita del escenario.

El sistema nunca convierte silenciosamente una corriente de flujo en corriente de diseño.

## In — protección

`In` se declara explícitamente y conserva referencia. Un rating visual o una ampacidad de conductor no se interpreta automáticamente como `In`.

## Iz_base

P3 mantiene separadas:

- ampacidad de catálogo P2;
- `Iz_base` normativa P3 obtenida de un dataset primario exacto.

Caso de referencia P3C10:

```text
dataset = PERU_CNE_UTIL_2006_TABLE_2_COL23_C_XLPE_3C_CU_70MM2_PRIMARY_V1
método = C
conductor = Cu 70 mm2 XLPE/EPR
conductores cargados = 3
Tabla 2, Col. 23
Iz_base = 229 A
ampacidad catálogo P2 = 296 A
```

Ambos valores permanecen trazables; uno no sustituye silenciosamente al otro.

## Factores de corrección

Cada factor debe tener valor, referencia y eje cuando el routing lo exige. Cuando existe dataset normativo, el factor se revalida contra el catálogo activo antes de entrar a Iz.

Si no se aplican factores, las condiciones base deben confirmarse expresamente. **P3 no asume silenciosamente `product(k_i)=1`.**

Los bindings automáticos solo existen para combinaciones cuya compatibilidad ha sido demostrada. Cobertura primaria de una tabla no implica binding universal.

### Limitación 5A

Tabla 5A está transcrita dentro de su alcance literal. Las columnas 20–25 permanecen fail-closed por la inconsistencia editorial identificada entre el alcance impreso de 5A y determinados routings de Tabla 3. No se aplica un factor por analogía.

## Resultado y madurez

`ampacity.evaluar()` devuelve:

- `CUMPLE`;
- `NO_CUMPLE`;
- `DATOS_INSUFICIENTES`.

Conserva Ib, In, Iz_base, origen de la base, factores, Iz, checks, routing, referencias, evidencia y madurez. La madurez se obtiene de una única fuente de verdad: `validation_status.ampacity = VALIDATED_WITH_LIMITATIONS`.

Un perfil se invalida si cambia su conductor, condición de instalación, ampacidad de catálogo, dataset normativo o contexto requerido. Los factores/base se revalidan en la evaluación, no solo al configurarlos.

## Readiness y matriz E

Para ampacidad:

```text
backend preferente = mcp
maturity = VALIDATED_WITH_LIMITATIONS
automatic_dispatch = false
professional_emission = false
```

El readiness de un modelo concreto puede bloquear parámetros faltantes, perfil `REFERENCE_ONLY`, revisión manual, mezcla CNE/IEC, factor requerido ausente o evidencia no profesional. Una fase P3 cerrada no convierte un modelo incompleto en apto para emisión.

## Workspace V3

V3 muestra, sin recalcular en JavaScript:

- Ib;
- In;
- Iz_base;
- origen y Tabla/dataset base;
- factores y producto `∏k`;
- Iz;
- estado;
- perfil/método/routing;
- calidad de evidencia;
- madurez y limitaciones.

El navegador solo presenta datos estructurados producidos por Python/MCP.

## Benchmarks

Los benchmarks P3B históricos mantienen `evidence_level = SECONDARY` y sirven para regresión de infraestructura.

P3C12 añade una referencia independiente, separada de los datasets de producción. La suite compara 29 casos de las seis familias requeridas y debe pasar 29/29. Incluye prueba de mutación para demostrar que el dataset no se valida contra sí mismo.

## Gate de salida P3

Estado P3-v1:

```text
P3C01-P3C13 = DONE
phase_status = READY_WITH_LIMITATIONS
ready_for_next_phase = true
next_phase = P4_IEC_60909
professional_emission = false
```

P3 puede seguir ampliando Tablas 1/2 y nuevos bindings de forma incremental sin reabrir el gate v1. La próxima fase principal es P4 IEC 60909; el `FaultStudy` actual de OpenDSS no debe presentarse todavía como IEC 60909.
