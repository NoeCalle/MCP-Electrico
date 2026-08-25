# P3C11A3 — Primera cadena normativa primaria completa A1 → Tabla 5A → Iz

## Objetivo

P3C11A2 implementó el binding fail-closed de factores `exact_rows_v1` hacia `Iz`, pero solo podía demostrar la rama compatible con una `Iz_base` sintética porque el catálogo primario real disponía únicamente del caso Método C / Tabla 2 Col. 23.

P3C11A3 incorpora una `Iz_base` primaria compatible con el subconjunto Tabla 5A ya verificado y demuestra por primera vez una cadena numérica completa usando exclusivamente evidencia oficial `PRIMARY_VERIFIED`.

## Fuente primaria

Fuente pinneada:

```text
MINEM_CNE_UTIL_2006_OFFICIAL_PDF
SHA-256 = 2b3cbd457c519bf9d9aa2cf2754c72b6e531708e45ea2fdf91f839b1acccfd64
```

La fila se encuentra en la misma captura oficial ya reproducida para P3C10C:

```text
PDF 552
Tablas - Pág. 5 de 82
Tabla 2 (continuación)
```

Revisión visual autorizada:

```text
Método A1
Cu
XLPE/EPR 90 °C
3 conductores cargados
70 mm²
Tabla 2 Col. 15
Iz_base = 179 A
```

Tabla 3 confirma el routing A1 + XLPE/EPR + 3 conductores cargados → Tabla 2 Col. 15.

La revisión queda registrada como `AI_VISUAL_REVIEW_USER_AUTHORIZED`, con `human_reviewer=null`. Se reutiliza el artefacto de extracción que ya verificó el SHA de la misma página oficial; no se usa una reproducción secundaria.

## Nuevo dataset

```text
PERU_CNE_UTIL_2006_TABLE_2_COL15_A1_XLPE_3C_CU_70MM2_PRIMARY_V1
```

Características:

- `axis = base_ampacity`;
- `verification_status = PRIMARY_VERIFIED`;
- `source_type = primary_official`;
- lookup exacto únicamente;
- sin interpolación;
- sin extrapolación;
- 70 mm² es la única sección incluida;
- cualquier otra consulta devuelve `VALUE_NOT_TABULATED`.

## Cadena primaria real

Para 35 °C:

```text
Iz_base = 179 A              Tabla 2 Col. 15 PRIMARY_VERIFIED
kT      = 0.96               Tabla 5A PRIMARY_VERIFIED
Iz      = 179 × 0.96
Iz      = 171.84 A
```

Para 40 °C:

```text
Iz_base = 179 A
kT      = 0.91
Iz      = 162.89 A
```

Los valores finales no se almacenan como nueva tabla. Son calculados por P3 a partir de la base y factor revalidados.

## Separación respecto del catálogo P2

El conductor físico utilizado por la regresión mantiene su ampacidad de catálogo P2:

```text
ampacidad catálogo P2 = 296 A
```

La cadena normativa usa:

```text
Iz_base CNE A1 = 179 A
```

No se sustituyen ni mezclan ambas magnitudes.

## Binding y revalidación

P3C11A2 ya exige coincidencia exacta de:

- referencia normativa;
- perfil P3A;
- método A1;
- ambiente aire;
- temperatura ambiente;
- aislamiento XLPE/EPR;
- Tabla 2;
- columna 15.

P3C11A3 demuestra el contrato con datasets reales. El factor vuelve a revalidarse al evaluar el estudio, por lo que un cambio posterior de contexto invalida la ficha en lugar de reutilizar un `kT` obsoleto.

## Visual V3

No se añade lógica eléctrica al navegador. Con esta cadena real, V3 ya puede presentar desde Python:

- `Iz base = 179 A`;
- origen `PRIMARIA`;
- `Tabla 2 col. 15` y dataset de base;
- `ambient_temperature: k=0.96` o `k=0.91`;
- `Tabla 5A` y dataset del factor;
- `Iz` resultante;
- estado `CUMPLE` / `NO_CUMPLE`.

## Efecto sobre el roadmap

Este bloque **no cierra P3C11**. Demuestra que la arquitectura de 5A funciona de extremo a extremo con evidencia primaria real, por lo que el esfuerzo siguiente debe concentrarse en cobertura normativa restante:

```text
5A: subconjunto primario + binding + cadena real demostrados
5B: pendiente
5C: subconjunto primario parcial; ampliar cobertura
5D: pendiente
5E: pendiente
```

El gate permanece:

```text
P3C01-P3C10 = DONE
P3C11 = PENDING
P3C12 = PENDING
P3C13 = PENDING
P3 = NOT_READY / UNDER_VALIDATION
P4 = bloqueada
professional_emission = false a nivel de fase
```

El próximo bloque recomendado del roadmap es **P3C11B — Tabla 5B, corrección por resistividad térmica del suelo para método D en ductos enterrados**.
