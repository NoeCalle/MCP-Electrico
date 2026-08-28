# Validaciones pendientes — MCP Eléctrico

Este documento registra validaciones que **no deben perderse del roadmap**, pero que actualmente no bloquean el uso interno de los módulos dentro de sus alcances matemáticos/técnicos declarados.

La existencia de una validación pendiente impide elevar el resultado a una afirmación más fuerte de conformidad o emisión profesional cuando corresponda.

## VP-IEC-01 — IEC 60909-0:2026 completa

**Estado:** `PENDING_LICENSED_IEC_REVIEW`

Pendiente disponer de acceso controlado al texto completo licenciado de IEC 60909-0:2026 Ed.3 y construir una matriz de trazabilidad cláusula/ecuación/implementación para los resultados que se pretendan promover como contractuales.

La revisión pública P4C10 permanece válida como `REVIEWED_WITH_LIMITATIONS_AGAINST_TARGET_EDITION`; no se transforma en `VERIFIED_AGAINST_TARGET_EDITION` sin este gate.

## VP-2FT-01 — semántica normativa de 2F-T

**Estado:** `PENDING_LICENSED_IEC_REVIEW`

El fundamento matemático 2F-T está auditado para falla b-c-tierra franca en red pasiva simétrica con `Z2=Z1`, pero está pendiente confirmar contra IEC 60909-0:2026 completa:

- definición/selección exacta de la magnitud 2F-T a promover como `Ik''`;
- factores de tensión y condiciones MAX/MIN aplicables;
- magnitudes adicionales que pueden o no promoverse;
- requisitos específicos de impedancias/equipos dentro del alcance final.

Hasta entonces `Ik''`, `Sk''`, `ip` e `Ith` 2F-T permanecen fail-closed a nivel contractual.

## VP-2FT-02 — caso externo independiente

**Estado:** `PENDING_EXTERNAL_REFERENCE_CASE`

Pendiente comparar una subestación reproducible contra una referencia externa independiente de confianza, por ejemplo:

- estudio previamente revisado/aprobado;
- software comercial reconocido usando los mismos datos y supuestos;
- benchmark publicado con datos suficientes para reproducir `Z1/Z2/Z0` y la falla 2F-T.

El benchmark matricial interno ya evita una comparación circular del algoritmo, pero no sustituye este contraste externo.

## VP-2FT-03 — revisión profesional

**Estado:** `PENDING_PROFESSIONAL_REVIEW`

Antes de habilitar emisión profesional de 2F-T debe revisarse al menos:

- topología y escenario MAX/MIN;
- `Z1/Z2/Z0` de la misma revisión del modelo;
- grupo vectorial y camino de secuencia cero;
- neutro/puesta a tierra;
- datos de cables/líneas relevantes;
- correspondencia entre la magnitud reportada y la finalidad del estudio.

## VP-P5C-01 — trazabilidad normativa completa de ratings de protección

**Estado:** `PENDING_LICENSED_STANDARD_REVIEW`

P5C puede comparar técnicamente una corriente de falla explícita contra `Icu` de un interruptor o `breaking_capacity_ka` de un fusible. Queda pendiente construir una matriz de aplicabilidad más completa contra los textos licenciados de las normas de producto relevantes, incluyendo al menos:

- IEC 60947-2:2024 para los interruptores modelados dentro de ese alcance;
- IEC 60269-1:2024 para los fusibles modelados dentro de ese alcance;
- relación entre tensión, categoría/condiciones del dispositivo y rating declarado;
- condiciones adicionales necesarias antes de promover el check a una afirmación de conformidad normativa.

Hasta entonces:

```text
full_standard_compliance_claim = false
professional_emission          = false
```

La regla P5C de no sustituir `Ics`/`Icw` por `Icu` permanece vigente independientemente de esta revisión futura.

## VP-P5C-02 — dataset trazable de coeficiente k / chequeo adiabático

**Estado:** `PENDING_NORMATIVE_DATASET`

P5C implementa matemáticamente:

```text
I²t <= k²S²
```

pero **no calcula automáticamente `k`** desde material, aislamiento o temperaturas. Queda pendiente incorporar un dataset normativo versionado y validado de `k` para los alcances que decidamos soportar profesionalmente.

Mientras este dataset no exista:

- `k` debe ser explícito;
- debe incluir `fuente_k`;
- una sección sin conductor P2 asignado requiere `fuente_seccion`;
- el PASS es un check adiabático con entradas declaradas, no una selección normativa automática del coeficiente.

## VP-P5C-03 — caso externo de protección/conductor

**Estado:** `PENDING_EXTERNAL_REFERENCE_CASE`

Pendiente contrastar al menos un alimentador real o benchmark publicado que incluya, con los mismos datos y supuestos:

- corriente de cortocircuito en el punto de instalación;
- dispositivo y rating de corte;
- conductor/sección;
- coeficiente `k` aplicable;
- tiempo de despeje trazable;
- resultado de soportabilidad térmica.

Este contraste se realizará cuando dispongamos de un caso externo adecuado; no bloquea el uso interno del check P5C con alcance declarado.

## Uso permitido mientras estas validaciones están pendientes

El fundamento 2F-T puede utilizarse internamente bajo el estado:

```text
mathematical_foundation = USABLE_WITH_DECLARED_SCOPE
normative_verification  = PENDING_LICENSED_IEC_REVIEW
external_reference_case = PENDING
professional_emission   = false
```

P5C puede utilizarse internamente bajo el estado:

```text
protection_checks              = EXPERIMENTAL
full_standard_compliance_claim = false
professional_emission          = false
```

No debe presentarse como certificación IEC integral ni utilizar la ausencia de estas validaciones como evidencia de cumplimiento normativo.

## Regla de cierre

Una validación de este archivo solo cambia a `DONE` cuando existe evidencia identificable en el repositorio o una revisión profesional documentada. No se cierra por inferencia, memoria o similitud con otra edición/caso.
