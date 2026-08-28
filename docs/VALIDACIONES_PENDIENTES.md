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

## Uso permitido mientras estas validaciones están pendientes

El fundamento 2F-T puede utilizarse internamente bajo el estado:

```text
mathematical_foundation = USABLE_WITH_DECLARED_SCOPE
normative_verification  = PENDING_LICENSED_IEC_REVIEW
external_reference_case = PENDING
professional_emission   = false
```

No debe presentarse como certificación IEC integral ni utilizar la ausencia de estas validaciones como evidencia de cumplimiento normativo.

## Regla de cierre

Una validación de este archivo solo cambia a `DONE` cuando existe evidencia identificable en el repositorio o una revisión profesional documentada. No se cierra por inferencia, memoria o similitud con otra edición/caso.
