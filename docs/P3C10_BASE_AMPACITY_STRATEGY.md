# P3C10 — Estrategia de ampacidad base normativa

## Estado

**P3C10A IMPLEMENTADO COMO CONTRATO; P3C10 CONTINÚA PENDIENTE.**

P3 foundation utiliza actualmente una ampacidad de catálogo P2 trazable como punto de partida. Esa información sigue siendo útil para el modelo físico y para detectar inconsistencias de producto/instalación, pero **no equivale por sí sola a una ampacidad base normativa CNE**.

P3C10 exige una estrategia validada para `Iz_base`. Dentro del alcance P3-v1, el router P3A ya establece:

- métodos A1/A2/B1/B2/C/D → Tabla 2;
- métodos E/F/G → Tabla 1.

## Separación de responsabilidades

La estrategia queda dividida en dos capas:

1. **P2 — catálogo/producto**: conductor seleccionado, sección, material, aislamiento, condición publicada, ampacidad de fabricante y procedencia;
2. **P3 — base normativa**: valor de Tabla 1/2 (o equivalente formalmente validado) obtenido mediante dataset versionado, lookup exacto y evidencia primaria.

El cálculo profesional futuro debe conservar ambas referencias y nunca sustituir silenciosamente una por la otra.

## Binding P3C10A

`ampacity_base_binding.py` introduce el contrato portable:

```text
lookup exacto P3B
    ↓
axis = base_ampacity
    ↓
table = Tabla 1 | Tabla 2
    ↓
Iz_base normativa + dataset/query/provenance
```

Reglas:

- solo acepta resultados `RESOLVED_EXACT`;
- solo acepta `axis=base_ampacity`;
- P3-v1 restringe la base a Tabla 1 o Tabla 2;
- el valor debe ser positivo;
- conserva `dataset_id`, query, estado de verificación y procedencia;
- antes de usarlo se revalida contra el catálogo activo;
- detecta manipulación del valor o de la tabla;
- una base secundaria requiere opt-in explícito y nunca se presenta como evidencia profesional;
- la ausencia de base normativa se clasifica expresamente como `P2_CATALOG`, no como primaria.

## Lo que este bloque NO hace

P3C10A no:

- incorpora valores numéricos de Tabla 1/2;
- inventa dimensiones de dichas tablas;
- modifica el dataset secundario 5C;
- declara `P3C10=DONE`;
- eleva la madurez de ampacidad;
- habilita emisión profesional.

El motor genérico `exact_rows_v1` ya permite que cada futura revisión primaria declare sus dimensiones exactas sin codificarlas antes de verificar la fuente oficial.

## P3C10B — integración al cálculo y V3

**IMPLEMENTADO COMO INFRAESTRUCTURA. P3C10 CONTINÚA PENDIENTE DE DATOS PRIMARIOS Tabla 1/2.**

El cálculo P3 puede recibir ahora una `base_normativa` portable producida por P3C10A. La base se revalida contra el catálogo activo antes de configurar y nuevamente al evaluar. La asignación P2 se conserva en paralelo para detectar cambios de conductor/instalación y para mostrar la diferencia entre catálogo y norma.

Cuando existe base normativa:

```text
Iz = Iz_base_normativa × ∏k
```

El resultado expone `base_evidence`, la fuente normativa de `Iz_base` y la fuente de catálogo P2 por separado. V3 añade la columna **Origen Iz base**, con clasificación preparada por Python: `CATÁLOGO P2`, `PRIMARIA`, `SECUNDARIA` o `INCOMPLETA`. El navegador continúa sin resolver tablas ni recalcular ingeniería.

La readiness de evidencia también exige base primaria: factores primarios con `Iz_base` todavía de catálogo P2 ya no pueden clasificarse como evidencia normativa profesional completa.

P3C10 solo podrá cerrar cuando exista al menos una estrategia/dataset Tabla 1/2 `PRIMARY_VERIFIED` real que satisfaga el gate formal y sus benchmarks correspondientes.
