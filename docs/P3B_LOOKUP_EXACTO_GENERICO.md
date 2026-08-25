# P3B — Lookup exacto genérico para datasets normativos

## Objetivo

Preparar la infraestructura para incorporar futuros datasets de ampacidad base y factores sin hardcodear hoy la estructura de Tablas 1/2, 5A, 5B, 5D o 5E que todavía no han sido verificadas contra una fuente primaria reproducible.

Este módulo **no agrega datos normativos** y no modifica la madurez de P3.

## Schema

Un futuro dataset puede declarar:

```text
lookup_schema.type = exact_rows_v1
lookup_schema.dimensions = [dimensión_1, dimensión_2, ...]
lookup_schema.value_field = factor | ampacity_a | otro campo numérico explícito
```

Cada fila declara exactamente esas dimensiones y un valor positivo.

El motor no conoce de antemano si una tabla usa temperatura, sección, material, método de instalación u otra dimensión. Esa estructura debe provenir de la revisión de la fuente normativa y quedar declarada en el dataset versionado.

## Política de resolución

`ampacity_exact_lookup.resolver_dataset()`:

- exige coincidencia exacta de dimensiones;
- normaliza únicamente equivalencia numérica `35` ↔ `35.0`;
- no interpola;
- no extrapola;
- no usa vecino más cercano;
- no completa dimensiones faltantes;
- no descarta dimensiones extra;
- rechaza queries duplicadas dentro del dataset.

Si no existe una fila exacta devuelve `VALUE_NOT_TABULATED`.

## Catálogo

`resolver_catalogo()` puede trabajar con un dataset registrado únicamente cuando este declare explícitamente `lookup_schema.type = exact_rows_v1`.

El dataset P3B 5C actual es legado y secundario. **No se migra implícitamente** y devuelve `DATASET_SCHEMA_NOT_GENERIC` al resolver genérico. Su resolver específico permanece intacto.

Esto evita cambiar la semántica del benchmark P3B existente o presentar una reestructuración de datos como nueva evidencia normativa.

## Evidencia y emisión

El motor genérico no salta la gobernanza existente:

- datasets secundarios siguen bloqueados por defecto;
- `PRIMARY_VERIFIED` continúa exigiendo fuente oficial pinneada y revisión;
- `professional_emission` solo puede ser true si la política del dataset y su evidencia primaria lo permiten;
- P3C08–P3C13 permanecen pendientes según el gate real.

## Uso futuro

Cuando se disponga de la publicación oficial reproducible, las dimensiones reales de cada subconjunto normativo podrán modelarse como datos. Por ejemplo, un dataset de temperatura podrá declarar sus dimensiones reales verificadas y uno de ampacidad base podrá declarar otras distintas, sin cambiar el algoritmo de lookup.

Los tests actuales usan exclusivamente fixtures sintéticos. Sus números no son valores del CNE ni de IEC y no deben citarse como tales.