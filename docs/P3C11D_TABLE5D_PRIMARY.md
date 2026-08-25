# P3C11D1 — Tabla 5D primaria completa

Se incorpora la **Tabla 5D completa** del CNE Utilización como dataset numérico `PRIMARY_VERIFIED` de agrupamiento para método D.

## Evidencia primaria

- fuente: `MINEM_CNE_UTIL_2006_OFFICIAL_PDF`;
- SHA-256: `2b3cbd457c519bf9d9aa2cf2754c72b6e531708e45ea2fdf91f839b1acccfd64`;
- Tabla 3 / routing: PDF 555, `Tablas - Pág. 8 de 82`;
- Tabla 5D rama A: PDF 566, `Tablas - Pág. 19 de 82`;
- Tabla 5D ramas B/C: PDF 567, `Tablas - Pág. 20 de 82`;
- captura reproducible: workflow run `32911061659`, artifact `9586544930`;
- digest artifact: `sha256:927949b5276c1515e82f04fe605f5d045d832ca8f2ef3bd980c0f3c5fc587442`.

## Estructura

La tabla no se reduce a un factor por número de circuitos. Se conservan tres ramas:

- `A_DIRECT_BURIED_CABLES`: cables directamente apoyados en tierra;
- `B_MULTICORE_SINGLE_WAY_DUCTS`: cable multipolar en ductos de una vía enterrados;
- `C_SINGLE_CORE_SINGLE_WAY_DUCT_CIRCUITS`: circuitos de cables unipolares en ductos de una vía enterrados.

Cada fila exige coincidencia exacta de rama, ambiente, número de circuitos/cables y separación.

## Condiciones publicadas

Los valores de Tabla 5D se publican para:

```text
profundidad = 0.7 m
resistividad térmica del suelo = 2.5 K·m/W
```

La nota de la tabla indica que son valores promedio y que el proceso de promedio/redondeo puede producir errores de hasta **±10 %**. Para valores más precisos remite a **IEC 60287**.

## Anomalía editorial preservada

En rama C, 6 circuitos y separación 1,0 m, el PDF imprime `,0,90`. El dataset conserva ese token en metadata y normaliza su valor numérico a `0.90`; no se oculta la anomalía de la publicación.

## Política

- `exact_rows_v1`;
- 65 filas verificadas;
- sin interpolación;
- sin extrapolación;
- `p3c11_family_coverage=true`;
- `automatic_binding_to_iz=false`.

D1 cierra **cobertura numérica de la familia 5D** dentro del alcance literal publicado, pero no habilita todavía su uso automático en `Iz`. P3C11D2 implementará clasificación de disposición y binding contextual.
