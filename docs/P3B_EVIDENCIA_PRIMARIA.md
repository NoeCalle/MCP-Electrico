# P3B — Gate de evidencia primaria

## Estado

**UNDER_VALIDATION.**

Este bloque evita que un dataset numérico pase de una transcripción secundaria a `PRIMARY_VERIFIED` por una simple edición de metadata.

La promoción normativa se trata como un proceso reproducible, versionado y de dos etapas: primero se fija la **fuente primaria**, después se verifica el **dataset** contra esa fuente.

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

Conocer una URL oficial no basta. Tampoco basta con calcular el hash de un archivo local cualquiera.

## Dos etapas obligatorias

### Etapa A — fijar la fuente oficial

Mientras una fuente esté:

```text
pin_status = DISCOVERED_UNPINNED
expected_sha256 = null
```

puede calcularse un SHA-256 candidato para diagnóstico, pero:

```text
eligible_as_primary_file = false
PRIMARY_EVIDENCE_READY_FOR_REVIEW = imposible
ELIGIBLE_FOR_PRIMARY_DATASET_PR = imposible
```

La huella de la copia oficial debe incorporarse mediante una revisión separada del registro de fuentes. El estado esperado después de esa revisión será:

```text
pin_status = PINNED
expected_sha256 = <64 hex>
```

El pin no certifica todavía ninguna tabla. Solo fija exactamente qué archivo/versionado se considera la fuente primaria de referencia.

### Etapa B — verificar el dataset contra la fuente pinneada

Una copia local solo puede servir como evidencia primaria si:

```text
sha256(copia_local) == expected_sha256
pinned_hash_match = true
```

Si el archivo difiere byte a byte, la evidencia queda bloqueada aunque tenga el mismo título, URL o contenido aparente.

## Flujo de evidencia

### 1. Verificar una copia local

`verificar_archivo_fuente_ampacidad()`:

- exige archivo existente;
- valida cabecera PDF;
- limita tamaño;
- calcula SHA-256;
- compara con el hash pinneado cuando exista;
- no inspecciona ni certifica tablas;
- devuelve siempre `professional_emission=false`.

Un hash calculado sobre una fuente `DISCOVERED_UNPINNED` es únicamente un **hash candidato**.

### 2. Construir paquete de evidencia

`construir_evidencia_primaria_ampacidad()` exige simultáneamente:

- fuente `PINNED` con SHA-256 válido;
- copia local con `pinned_hash_match = true`;
- tablas verificadas;
- referencias de página/sección;
- revisor identificado;
- confirmación explícita de comparación manual.

Solo entonces devuelve:

`PRIMARY_EVIDENCE_READY_FOR_REVIEW`

Esto **no significa** `PRIMARY_VERIFIED`.

### 3. Evaluar elegibilidad de una revisión primaria

`evaluar_promocion_dataset_ampacidad()` vuelve a comprobar, de forma independiente:

- fuente `PINNED`;
- igualdad exacta entre `file_sha256` y `expected_sha256`;
- referencia normativa del dataset y de la fuente;
- tabla del dataset vs. tablas revisadas;
- clase de la fuente;
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

`ampacity_datasets.validar_dataset_record()` se ejecuta al cargar el catálogo y constituye una segunda barrera independiente.

Un dataset `PRIMARY_VERIFIED` debe declarar como mínimo:

- `source_type = primary_official`;
- `primary_source_id`;
- `source_sha256` válido de 64 caracteres hexadecimales;
- `page_references` no vacías;
- `verification_record.reviewer`;
- `verification_record.manual_comparison_confirmed = true`.

Además el loader cruza esa metadata con `ampacity_primary_sources.json` y exige:

- que `primary_source_id` exista;
- que la fuente sea `OFFICIAL_PRIMARY_CANDIDATE`;
- que esté `PINNED`;
- que su `expected_sha256` sea válido;
- que `dataset.provenance.source_sha256 == source.expected_sha256`;
- que `norm_reference_id` coincida.

Por tanto, incluso una edición manual aparentemente completa del JSON hace fallar el loader y CI si intenta usar una fuente no pinneada o un hash diferente.

Un dataset que no sea `PRIMARY_VERIFIED` tampoco puede declarar `professional_emission=true`.

## Lo que este gate no demuestra

Superar todas estas barreras no demuestra por sí solo:

- que la transcripción numérica sea correcta;
- que la interpretación de la tabla sea correcta;
- que el alcance del método de instalación sea correcto;
- que el dataset cubra toda la norma;
- que P3 esté cerrado.

Después de crear una revisión primaria todavía se requieren benchmarks independientes y el gate formal de salida P3.

## Estado actual

A la fecha de implementación de este bloque:

- fuente oficial: descubierta, **no pinneada**;
- dataset 5C inicial: `PENDING_PRIMARY_VERIFICATION`;
- benchmark P3B: evidencia `SECONDARY`;
- `ampacity`: `UNDER_VALIDATION`;
- emisión profesional automática: deshabilitada.
