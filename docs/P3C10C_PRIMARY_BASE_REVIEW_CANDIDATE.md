# P3C10C — Evidencia candidata de ampacidad base Tabla 2

## Estado

**EVIDENCIA CANDIDATA REGISTRADA; REVISIÓN HUMANA PENDIENTE.**

Este bloque no crea todavía un dataset `PRIMARY_VERIFIED`. Su objetivo es fijar un primer caso mínimo de `Iz_base` contra la copia oficial CNE ya pinneada, con estructura, página, columna y routing reproducibles.

## Descubrimiento de Tablas 1 y 2

La ejecución reproducible `32880258067` volvió a descargar la fuente `MINEM_CNE_UTIL_2006_OFFICIAL_PDF` y exigió coincidencia exacta con:

```text
sha256 = 2b3cbd457c519bf9d9aa2cf2754c72b6e531708e45ea2fdf91f839b1acccfd64
```

La estructura localizada es:

- Tabla 1: páginas PDF 548–550 (`Tablas - Pág. 1–3 de 82`);
- Tabla 2: páginas PDF 551–554 (`Tablas - Pág. 4–7 de 82`);
- Tabla 3 de métodos referenciales y correspondencia tabla/columna: página PDF 555 (`Tablas - Pág. 8 de 82`).

El artefacto `9575497393` conserva el JSON de descubrimiento y las páginas renderizadas para revisión.

## Primer caso mínimo candidato

Para no cargar una tabla completa antes de validar el proceso se selecciona un único punto:

```text
Norma:       PERU_CNE_UTILIZACION_2006
Perfil:      PERU_CNE_UTIL_2006_030_004
Tabla:       Tabla 2
Método:      C
Material:    Cobre
Aislamiento: XLPE/EPR
Temperatura: 90 °C
Conductores de carga: 3
Sección:     70 mm²
Columna:     23
Iz_base candidata: 229 A
```

La página de Tabla 2 es la PDF 552, marcador `Tablas - Pág. 5 de 82`. La Tabla 3 en PDF 555 fija para método C con XLPE/EPR las columnas 22 y 23 para 2 y 3 conductores cargados, respectivamente.

## Barrera de revisión

El registro conserva expresamente:

```text
manual_comparison_confirmed = false
human_reviewer = null
eligible_for_primary_dataset_pr = false
professional_emission = false
```

Por tanto, este bloque:

- no declara el valor como `PRIMARY_VERIFIED`;
- no crea aún un dataset de producción Tabla 2;
- no marca `P3C10=DONE`;
- no eleva la madurez de ampacidad;
- no habilita emisión profesional.

## Relación con P3C10A/B y V3

P3C10A ya define el binding `dataset -> Iz_base`, y P3C10B ya permite utilizar una base normativa revalidada en el cálculo, preservando en paralelo el catálogo P2. Este candidato es la primera evidencia real que, una vez revisada y promovida correctamente, podría alimentar ese contrato.

V3 ya distingue `Origen Iz base` de `Evidencia factores`; hasta que este candidato sea revisado/promovido, el sistema no debe mostrarlo como base primaria de un estudio.

## Siguiente paso

Revisión humana del punto candidato y de la correspondencia Tabla 3 → Tabla 2 Col. 23. Solo después se podrá crear una revisión numérica `PRIMARY_VERIFIED` pequeña y someterla a benchmark independiente antes de considerar avance formal de P3C10.
