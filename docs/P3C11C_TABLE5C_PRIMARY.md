# P3C11C1 — Tabla 5C primaria completa

Se incorpora la **Tabla 5C completa** del CNE Utilización como dataset `PRIMARY_VERIFIED` para factores de reducción por agrupamiento.

## Evidencia

- fuente oficial pinneada: `MINEM_CNE_UTIL_2006_OFFICIAL_PDF`;
- SHA-256: `2b3cbd457c519bf9d9aa2cf2754c72b6e531708e45ea2fdf91f839b1acccfd64`;
- PDF 565 / `Tablas - Pág. 18 de 82`;
- render/texto reproducibles conservados desde workflow `32877141382`, artifact `9574334684`;
- digest del artifact: `sha256:484dc013f71dfe7974df88815f364cf6c93dc8233e5b1d7b855e07a36577aefb`.

El subconjunto histórico 2→0,80; 3→0,70; 12→0,45 permanece intacto. C1 añade una **nueva revisión completa**, sin mutar las revisiones anteriores.

## Cinco ítems publicados

1. agrupados en el aire, sobre superficie, empotrados o encerrados;
2. una capa sobre pared, piso o bandeja no perforada;
3. una capa fijada directamente bajo techo de madera;
4. una capa sobre bandeja perforada horizontal o vertical;
5. una capa sobre soporte de bandeja de escaleras, listones, etc.

La referencia de uso también se conserva estructurada:

- ítem 1: columnas 4–8 / métodos A–F;
- ítems 2–3: columnas 4–7 / método C;
- ítems 4–5: columnas 8–9 / métodos E–F.

C1 **no convierte todavía esas referencias en un binding automático**. Esa clasificación pertenece a C2.

## Valores y regla para más de nueve circuitos

El ítem 1 conserva exclusivamente las columnas publicadas:

`1,2,3,4,5,6,7,8,9,12,16,20`.

Por tanto una consulta como 10 u 11 circuitos no se interpola.

En los ítems 2–5, la tabla publica una regla combinada:

> No más factores de reducción para más de nueve circuitos o cables multipolares.

El dataset la representa mediante la categoría normativa `9_or_more`, asociada al factor publicado en la columna 9. Esto **no se etiqueta ni se implementa como extrapolación matemática**: es una regla categórica de la propia tabla.

## Notas normativas preservadas

- aplica a grupos uniformes de cables igualmente cargados;
- si la separación horizontal entre cables adyacentes excede dos veces su diámetro total, no se requiere factor de reducción;
- el mismo factor se aplica a grupos de dos o tres cables unipolares y a cables multipolares;
- se conservan las reglas de conteo de circuitos de las Notas 4 y 5;
- los valores son promedios y la precisión total indicada está dentro de ±5 %;
- para configuraciones no cubiertas pueden requerirse factores específicos, por ejemplo Tabla 5E.

## Shard de datos

C1 introduce soporte de **shards explícitos** en `ampacity_datasets` para evitar que el catálogo normativo continúe creciendo como un único JSON monolítico.

La carga:

- conserva el catálogo histórico;
- agrega únicamente shards listados explícitamente;
- valida cada registro con el mismo gate `PRIMARY_VERIFIED`;
- rechaza IDs duplicados entre archivos (`P3B023`).

No se hace descubrimiento por glob ni se cargan archivos temporales accidentalmente.

## Política C1

- `exact_rows_v1`;
- 48 filas numéricas exactas;
- `p3c11_family_coverage=true`;
- `professional_emission=true` para lookup exacto dentro del dataset;
- `automatic_binding_to_iz=false`;
- sin interpolación ni extrapolación.

Con C1, y una vez que E1 esté mergeado, las familias 5B/5C/5D/5E quedan con cobertura primaria completa. **Tabla 5A pasa a ser la única familia pendiente de P3C11.**
