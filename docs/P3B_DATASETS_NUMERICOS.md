# P3B — Datasets numéricos de ampacidad

## Estado

**UNDER_VALIDATION.**

P3B incorpora la infraestructura para resolver factores y bases numéricas desde datasets versionados sin confundir **dato disponible** con **dato aprobado para emisión profesional**.

La regla principal es:

> Un valor numérico solo puede habilitar evidencia normativa automática profesional si su dataset tiene procedencia primaria verificada, una fuente oficial pinneada y una política de uso que lo permita.

La aptitud de un dataset puntual no eleva por sí sola la madurez global de P3 ni habilita `professional_emission` de la fase.

## Estados de evidencia

Los datasets declaran al menos:

- `source_type`;
- `verification_status`;
- fuente/publisher/URL;
- fecha de acceso o registro de revisión;
- alcance exacto;
- política de interpolación/extrapolación;
- `professional_emission`.

P3B diferencia, entre otros:

- `PRIMARY_VERIFIED`: contenido contrastado contra fuente primaria/versionada y pinneada;
- `PENDING_PRIMARY_VERIFICATION`: valor disponible pero pendiente de contraste primario;
- `SECONDARY_TRANSCRIPTION`: transcripción/reproducción secundaria.

Un dataset secundario puede utilizarse en desarrollo únicamente mediante opt-in explícito. Su resultado conserva:

```text
professional_emission = false
automatic_normative_lookup = false
```

## Dataset histórico de infraestructura

`PERU_CNE_UTIL_2006_TABLE_5C_ITEM1_SECONDARY_V1`

Alcance:

- perfil: `PERU_CNE_UTIL_2006_030_004`;
- eje: `grouping`;
- tabla: Tabla 5C;
- disposición: `grouped_air_surface_embedded_enclosed`;
- lookup exacto únicamente;
- sin interpolación;
- sin extrapolación.

Fuente de desarrollo: reproducción de la Tabla 5C en Cybertesis de la Universidad Nacional Mayor de San Marcos, cuya propia tabla declara como fuente al CNE Utilización.

URL registrada:

`https://cybertesis.unmsm.edu.pe/backend/api/core/bitstreams/9109b64f-62ef-4504-b242-946dbcb41301/content`

El dataset **no se considera fuente primaria** y no habilita emisión.

### Casos fijados para benchmark de infraestructura

Se fijaron antes de ejecutar CI tres casos exactos dentro de la misma fila reproducida:

- 2 circuitos → factor 0.80;
- 3 circuitos → factor 0.70;
- 12 circuitos → factor 0.45.

Estos casos prueban lectura, selección exacta, trazabilidad y política de seguridad. **No prueban que la tabla normativa esté validada contra la publicación primaria.**

## Revisiones PRIMARY_VERIFIED disponibles

### Tabla 5C — agrupamiento, subconjunto P3C09

`PERU_CNE_UTIL_2006_TABLE_5C_ITEM1_PRIMARY_V1`

Contiene deliberadamente solo las celdas contrastadas contra la copia oficial pinneada:

- 2 circuitos → 0.80;
- 3 circuitos → 0.70;
- 12 circuitos → 0.45.

No muta ni reemplaza la revisión secundaria histórica. Las demás posiciones siguen fuera del subconjunto primario mientras no se revisen explícitamente.

### Tabla 2 — `Iz_base`, caso P3C10

`PERU_CNE_UTIL_2006_TABLE_2_COL23_C_XLPE_3C_CU_70MM2_PRIMARY_V1`

Consulta exacta verificada:

```text
installation_method = C
conductor_material = Cu
insulation = XLPE_EPR
temperature_c = 90
loaded_conductors = 3
section_mm2 = 70.0
Tabla 2, Col. 23
ampacity_a = 229.0
```

La Tabla 3 aporta la evidencia de routing **Método C + XLPE/EPR + 3 conductores cargados → Tabla 2 Col. 23**. El dataset usa `lookup_schema=exact_rows_v1` y contiene una sola fila. Una consulta distinta devuelve `VALUE_NOT_TABULATED`; no se interpola, extrapola ni selecciona vecino más cercano.

Esta revisión cierra la estrategia P3C10 de `Iz_base` de extremo a extremo, pero **no declara cargada o validada la Tabla 2 completa ni la Tabla 1 completa**.

## Sin interpolación ni extrapolación

P3B no calcula valores entre posiciones tabuladas. Si el dataset contiene, por ejemplo, 9 y 12 circuitos pero se solicitan 10, devuelve:

`VALUE_NOT_TABULATED`

No se aproxima 10 por interpolación. La misma regla se aplica a secciones, métodos, aislamiento, número de conductores cargados y cualquier dimensión declarada por `exact_rows_v1`.

## Coherencia con P3A

El lookup P3B debe coincidir con el escenario declarado por P3A:

- perfil normativo;
- método de instalación;
- cantidad de circuitos agrupados cuando aplique;
- disposición cuando fue declarada;
- dimensiones exactas de la base normativa cuando se usa `base_ampacity`.

Si se pide un factor con una cantidad/disposición diferente al routing activo, P3B devuelve `ROUTE_MISMATCH` en los resolvers específicos. Los datasets genéricos exigen coincidencia exacta de todas sus dimensiones.

## Corrección técnica incorporada durante P3B

La auditoría del CNE durante esta fase detectó que el **método D enterrado** requiere una ruta específica de agrupamiento por **Tabla 5D**. P3A fue corregido para no tratarlo como la rama genérica 5C.

Por ahora:

- P3A identifica Tabla 5D para método D agrupado;
- exige contexto de disposición/separación;
- mantiene `MANUAL_REVIEW_REQUIRED`;
- P3B no reutiliza el dataset 5C para método D;
- el dataset numérico 5D queda pendiente.

## Gate de evidencia primaria

P3B registra las fuentes oficiales de forma separada a los datasets. La fuente CNE en `gob.pe` ya quedó fijada como copia primaria de referencia:

```text
source_class = OFFICIAL_PRIMARY_CANDIDATE
pin_status = PINNED
expected_sha256 = 2b3cbd457c519bf9d9aa2cf2754c72b6e531708e45ea2fdf91f839b1acccfd64
```

La captura reproducible se realizó desde la URL oficial registrada mediante GitHub Actions run `32875620716`, con tamaño `10829258` bytes. El pin identifica exactamente el archivo utilizado por el proyecto; **no significa que MINEM publique ese hash ni que las tablas hayan sido verificadas automáticamente**.

El proceso sigue siendo obligatoriamente de dos etapas:

1. **fijar la fuente primaria** — P3C08 ya completado para este CNE;
2. **verificar cada dataset/subconjunto** — la copia usada debe tener exactamente ese SHA-256 y luego contrastarse tabla/página por tabla/página.

Después del pin, el flujo exige:

1. copia cuyo SHA-256 coincida exactamente con `expected_sha256`;
2. tablas verificadas;
3. referencias de página/sección;
4. revisor identificado y modalidad de revisión trazable;
5. confirmación de comparación explícita; si la modalidad es IA visual, debe conservar autorización expresa del usuario;
6. evaluación de elegibilidad;
7. **nueva revisión del dataset por PR + CI**.

El mejor resultado previo al PR es `ELIGIBLE_FOR_PRIMARY_DATASET_PR`. No existe promoción automática y ese estado mantiene `professional_emission=false`.

Además, el loader del catálogo aplica `validar_dataset_record()` y cruza cualquier `PRIMARY_VERIFIED` con `ampacity_primary_sources.json`. Exige fuente existente, oficial candidata, `PINNED`, hash idéntico, misma referencia normativa, páginas y registro de revisión. Una edición manual inconsistente hace fallar la carga y CI.

Detalle del proceso: `docs/P3B_EVIDENCIA_PRIMARIA.md`.

## Binding P3B → Ib/In/Iz

### Factores de corrección

`ampacity_factor_binding.py` transporta un factor resuelto hasta el cálculo P3 sin convertirlo en un simple número anónimo. Conserva:

- `dataset_id`;
- `axis`;
- valor exacto;
- tabla;
- consulta de método/circuitos/disposición;
- `verification_status`;
- procedencia del dataset;
- `professional_emission`;
- `automatic_normative_lookup`.

Al configurar `Ib/In/Iz`, P3 **revalida** el factor contra el catálogo activo. Si alguien modifica el valor o la consulta después del lookup, la configuración se bloquea.

Para un dataset secundario se requieren dos consentimientos explícitos distintos:

1. `permitir_dataset_secundario=true` para obtener el valor desde P3B;
2. `permitir_factores_dataset_secundarios=true` para permitir que ese factor entre al cálculo P3.

Esto evita que un valor secundario obtenido para inspección/desarrollo termine accidentalmente dentro de `Iz`.

Ejemplo histórico de desarrollo con base P2 y factor secundario:

```text
Iz_base catálogo P2 = 296 A
k_group = 0.80
Iz = 296 × 0.80 = 236.8 A
```

El resultado puede evaluarse técnicamente, pero conserva:

```text
factor_evidence.contains_secondary = true
automatic_normative_lookup = false
professional_emission = false
maturity = UNDER_VALIDATION
```

### Base normativa `Iz_base`

`ampacity_base_binding.py` aplica el mismo principio de trazabilidad para `axis=base_ampacity`. Un resultado exacto de Tabla 1/2 se convierte en `base_p3`, se revalida contra el catálogo activo y entra al cálculo como `base_normativa`.

Para el caso primario P3C10:

```text
ampacidad catálogo P2 = 296 A
Iz_base normativa CNE = 229 A
```

Ambas referencias permanecen en el resultado. El valor de catálogo conserva su función P2 y la base normativa conserva dataset, tabla, query y procedencia primaria. No son intercambiables.

Un conjunto de factores puede reportar `automatic_normative_lookup=true` únicamente si **todos** los factores aplicados provienen de datasets P3B primarios/verificados y ninguno es manual o secundario. La base normativa se evalúa por separado. Estos indicadores no cambian por sí solos la madurez global P3 ni habilitan emisión mientras el módulo continúe `UNDER_VALIDATION`.

## Benchmark reproducible

`examples/run_benchmarks_p3b.py` genera:

`benchmark_p3b.json`

El benchmark histórico de infraestructura mantiene explícitamente:

- `failed = 0`;
- `pass = true`;
- `evidence_level = SECONDARY`;
- `professional_emission = false`.

Esto evita que un benchmark verde se interprete erróneamente como validación normativa primaria. Los benchmarks independientes necesarios para P3C12 se registran por una vía de evidencia separada.

## Siguiente paso P3B

P3C09 queda cerrado con `PERU_CNE_UTIL_2006_TABLE_5C_ITEM1_PRIMARY_V1` y P3C10 queda cerrado con `PERU_CNE_UTIL_2006_TABLE_2_COL23_C_XLPE_3C_CU_70MM2_PRIMARY_V1`.

El siguiente bloque principal es **P3C11**:

1. ampliar cobertura primaria 5A/5B/5C/5D/5E dentro del alcance declarado;
2. mantener Tabla 5D separada para método D y Tabla 5E solo donde corresponda por disposición;
3. continuar ampliando Tablas 1/2 únicamente mediante nuevas filas exactas verificadas cuando sean necesarias, sin convertir P3C10 en una afirmación de cobertura exhaustiva;
4. incorporar benchmarks normativos primarios independientes para P3C12;
5. elevar madurez únicamente cuando la evidencia permita cerrar P3C13.

P3 permanece `UNDER_VALIDATION`: que un dataset puntual tenga `professional_emission=true` significa que **ese subconjunto exacto** puede sustentar evidencia normativa; no habilita por sí mismo la emisión profesional automática del estudio completo.