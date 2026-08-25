# P3C11E1 — Tabla 5E primaria completa

Se incorpora la **Tabla 5E completa** del CNE Utilización como dataset `PRIMARY_VERIFIED` para agrupamiento de circuitos al aire libre.

## Evidencia

- fuente oficial pinneada: `MINEM_CNE_UTIL_2006_OFFICIAL_PDF`;
- SHA-256: `2b3cbd457c519bf9d9aa2cf2754c72b6e531708e45ea2fdf91f839b1acccfd64`;
- rama A: PDF 568, `Tablas - Pág. 21 de 82`;
- rama B: PDF 569, `Tablas - Pág. 22 de 82`;
- routing/base: Tabla 1, PDF 548-549;
- captura reproducible: run `32912314189`, artifact `9586942706`;
- digest: `sha256:ab88f4455ee09ed2332a878ddb06044515224635136fff1c5e34e69ed8cada8e`.

## Dos ramas normativas

### A — cables multipolares, método E

Conserva tipo de soporte, contacto/espaciado, número de bandejas y número de cables. Se distinguen bandejas perforadas, bandejas perforadas verticales y bandejas de escalera/abrazaderas.

### B — circuitos trifásicos de cables unipolares, método F

Además de soporte, contacto/espaciado y número de bandejas, conserva la formación de los tres cables: horizontal, vertical o triángulo.

La Nota 2 de la rama B exige que, cuando exista más de un cable en paralelo por fase, **cada juego trifásico se considere un circuito** para seleccionar el factor.

## Cobertura completa

La publicación contiene:

```text
134 celdas numéricas
10 celdas marcadas "-"
```

Las 134 celdas numéricas se almacenan como filas `exact_rows_v1`. Las 10 posiciones no tabuladas se preservan explícitamente en `not_tabulated_cells`; no se inventa valor ni se interpola.

## Límites

- una sola capa de cables o grupos en triángulo según la rama;
- los valores son promedios y su extensión es generalmente menor de ±5 %;
- espaciamientos menores a los publicados requieren factores menores, que MCP **no infiere**;
- sin interpolación ni extrapolación.

## Política E1

- `p3c11_family_coverage=true`;
- `professional_emission=true` para lookups exactos dentro del dataset;
- `automatic_binding_to_iz=false`.

E1 cierra la cobertura numérica de 5E. E2 deberá clasificar de forma estructurada soporte, orientación, formación y separación antes de permitir 5E→`Iz` y mostrar esa evidencia en V3.
