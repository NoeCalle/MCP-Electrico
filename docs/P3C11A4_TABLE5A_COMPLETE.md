# P3C11A4 — Tabla 5A primaria completa

P3C11A4 incorpora la **Tabla 5A completa** del CNE Utilización como evidencia numérica `PRIMARY_VERIFIED` para el eje de corrección por temperatura ambiente.

## Fuente

- fuente oficial pinneada: `MINEM_CNE_UTIL_2006_OFFICIAL_PDF`;
- SHA-256: `2b3cbd457c519bf9d9aa2cf2754c72b6e531708e45ea2fdf91f839b1acccfd64`;
- Tabla 5A: PDF 563 / `Tablas - Pág. 16 de 82`;
- routing de columnas: Tabla 3, PDF 555;
- revisión visual: `AI_VISUAL_REVIEW_USER_AUTHORIZED`;
- `human_reviewer=null`.

## Cobertura publicada

La página contiene dos bloques.

### Bloque normal

Factores para temperatura ambiente distinta de 30 °C en cables al aire y distinta de 20 °C en cables en ductos enterrados. La propia Tabla 5A declara este bloque aplicable a las **columnas 2 a 16 de las Tablas 1 y 2**.

Se preservan seis columnas de factores:

- `PVC_AIR`;
- `PVC_BURIED_DUCT`;
- `XLPE_EPR_AIR`;
- `XLPE_EPR_BURIED_DUCT`;
- `MI_PVC_OR_BARE_NOT_EXPOSED_70C`;
- `MI_BARE_NOT_EXPOSED_105C`.

### Conductores con mayor temperatura de operación

La publicación declara este bloque aplicable a las **columnas 17, 18 y 19 de las Tablas 1 y 2**:

- columna 17 → `AL_ALA_125C`;
- columna 18 → `A_AA_FEP_FEPB_200C`;
- columna 19 → `TFE_250C`.

## Conteo de celdas

La transcripción completa conserva:

```text
111 valores numéricos
45 posiciones publicadas como "-"
```

Los guiones permanecen como `VALUE_NOT_TABULATED`. No se transforman en 1,0, cero, vecino más cercano ni valor interpolado.

## Conflicto de alcance: columnas 20–25

Tabla 3 utiliza también columnas posteriores para determinadas combinaciones de método/aislamiento, mientras Tabla 5A declara literalmente sus bloques para columnas 2–16 y 17–19.

P3C11A4 adopta una política conservadora:

```text
columnas 2–16  -> bloque NORMAL publicado
columnas 17–19 -> bloque HIGH_OPERATING_TEMPERATURE publicado
columnas 20–25 -> FAIL_CLOSED
```

No se extienden factores por analogía a las columnas 20–25. Resolver esa aplicabilidad requerirá evidencia normativa adicional o una decisión técnica formal separada.

## Lookup y binding

`ampacity_table5a.resolver_celda()` permite consultar exactamente la evidencia publicada y devuelve `RESOLVED_EXACT`, `VALUE_NOT_TABULATED` o `SCOPE_MISMATCH`.

El dataset completo declara:

```text
p3c11_family_coverage = true
professional_emission = true  # para evidencia/celda exacta dentro de alcance
automatic_binding_to_iz = false
```

Esto **no elimina** el binding 5A ya validado para el subconjunto A1 / Tabla 2 col.15. El dataset parcial histórico conserva `automatic_binding_to_iz=true` para esa cadena demostrada. La cobertura completa y la automatización general son estados diferentes.

## Efecto en el roadmap

Con E1 (5E), C1 (5C) y A4 (5A), las familias 5A/5B/5C/5D/5E quedan con cobertura primaria completa dentro del gate P3-v1. Por tanto, `P3C11` puede pasar a `DONE`.

Esto **no cierra P3**. Permanecen bloqueantes:

- `P3C12` — benchmarks normativos independientes con evidencia primaria por familia;
- `P3C13` — madurez de ampacidad al menos `VALIDATED_WITH_LIMITATIONS`.

P4 IEC 60909 continúa bloqueada hasta cerrar formalmente P3.

## Contrato de cierre P3C11

El estado esperado después de integrar este bloque es explícitamente:

```text
P3C01-P3C11 = DONE
P3C12       = PENDING
P3C13       = PENDING
P3          = NOT_READY
P4          = BLOQUEADA
```

Este contrato evita confundir cobertura normativa completa con validación independiente o madurez profesional de la fase.
