# P3B — Gate de evidencia primaria

## Estado

**UNDER_VALIDATION.**

Este bloque evita que un dataset numérico pase de una transcripción secundaria a `PRIMARY_VERIFIED` por una simple edición de metadata.

La promoción normativa se trata como un proceso reproducible y versionado.

## Fuente oficial candidata registrada

`MINEM_CNE_UTIL_2006_OFFICIAL_PDF`

- autoridad: Ministerio de Energía y Minas del Perú;
- documento: Código Nacional de Electricidad — Utilización;
- referencia: R.M. N.° 0037-2006-MEM;
- landing oficial: `https://www.gob.pe/institucion/minem/normas-legales/108855-0037-2006-mem`;
- PDF descubierto en CDN oficial `gob.pe`;
- estado actual: `DISCOVERED_UNPINNED`;
- `expected_sha256 = null`.

El entorno de desarrollo logró descubrir la ubicación oficial, pero no descargar el PDF de forma reproducible. Por eso **no existe todavía una huella oficial fijada y ningún dataset se promueve**.

## Flujo de evidencia

### 1. Verificar una copia local

`verificar_archivo_fuente_ampacidad()`:

- exige archivo existente;
- valida cabecera PDF;
- limita tamaño;
- calcula SHA-256;
- compara con hash fijado cuando exista;
- no inspecciona ni certifica tablas;
- devuelve siempre `professional_emission=false`.

### 2. Construir paquete de evidencia

`construir_evidencia_primaria_ampacidad()` exige:

- SHA-256 de la copia local;
- tablas verificadas;
- referencias de página/sección;
- revisor identificado;
- confirmación explícita de comparación manual.

Solo entonces devuelve:

`PRIMARY_EVIDENCE_READY_FOR_REVIEW`

Esto **no significa** `PRIMARY_VERIFIED`.

### 3. Evaluar elegibilidad de una revisión primaria

`evaluar_promocion_dataset_ampacidad()` compara:

- referencia normativa del dataset y de la fuente;
- tabla del dataset vs. tablas revisadas;
- clase de la fuente;
- integridad del SHA-256;
- completitud del paquete.

El mejor resultado posible es:

`ELIGIBLE_FOR_PRIMARY_DATASET_PR`

Aun así:

```text
automatic_promotion = false
professional_emission = false
```

La acción siguiente obligatoria es crear una **nueva revisión del dataset en Git**, con su evidencia, y someterla a PR + CI.

## Gate del propio catálogo

`ampacity_datasets.validar_dataset_record()` se ejecuta al cargar el catálogo.

Un dataset `PRIMARY_VERIFIED` debe declarar como mínimo:

- `source_type = primary_official`;
- `primary_source_id`;
- `source_sha256` válido de 64 caracteres hexadecimales;
- `page_references` no vacías;
- `verification_record.reviewer`;
- `verification_record.manual_comparison_confirmed = true`.

Además, un dataset que no sea `PRIMARY_VERIFIED` no puede declarar `professional_emission=true`.

Por tanto, una edición manual incompleta del JSON hace fallar el loader y CI.

## Lo que este gate no demuestra

Superar el gate estructural no demuestra por sí solo:

- que la transcripción numérica sea correcta;
- que la interpretación de la tabla sea correcta;
- que el alcance del método de instalación sea correcto;
- que el dataset cubra toda la norma;
- que P3 esté cerrado.

Después de crear una revisión primaria todavía se requieren benchmarks independientes y el gate formal de salida P3.

## Estado actual

A la fecha de implementación de este bloque:

- fuente oficial: descubierta, no fijada por hash;
- dataset 5C inicial: `PENDING_PRIMARY_VERIFICATION`;
- benchmark P3B: evidencia `SECONDARY`;
- `ampacity`: `UNDER_VALIDATION`;
- emisión profesional automática: deshabilitada.
