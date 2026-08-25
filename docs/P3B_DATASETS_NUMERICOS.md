# P3B — Datasets numéricos de ampacidad

## Estado

**UNDER_VALIDATION.**

P3B incorpora la infraestructura para resolver factores numéricos desde datasets versionados sin confundir **dato disponible** con **dato aprobado para emisión profesional**.

La regla principal es:

> Un valor numérico solo puede habilitar cálculo normativo automático profesional si su dataset tiene procedencia primaria verificada, una fuente oficial pinneada y una política de uso que lo permita.

## Estados de evidencia

Los datasets declaran al menos:

- `source_type`;
- `verification_status`;
- fuente/publisher/URL;
- fecha de acceso;
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

## Dataset inicial

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

## Sin interpolación ni extrapolación

P3B no calcula valores entre posiciones tabuladas. Si el dataset contiene, por ejemplo, 9 y 12 circuitos pero se solicitan 10, devuelve:

`VALUE_NOT_TABULATED`

No se aproxima 10 por interpolación.

## Coherencia con P3A

El lookup P3B debe coincidir con el escenario declarado por P3A:

- perfil normativo;
- método de instalación;
- cantidad de circuitos agrupados;
- disposición cuando fue declarada.

Si se pide un factor con una cantidad/disposición diferente al routing activo, P3B devuelve `ROUTE_MISMATCH`.

## Corrección técnica incorporada durante P3B

La auditoría del CNE durante esta fase detectó que el **método D enterrado** requiere una ruta específica de agrupamiento por **Tabla 5D**. P3A fue corregido para no tratarlo como la rama genérica 5C.

Por ahora:

- P3A identifica Tabla 5D para método D agrupado;
- exige contexto de disposición/separación;
- mantiene `MANUAL_REVIEW_REQUIRED`;
- P3B no reutiliza el dataset 5C para método D;
- el dataset numérico 5D queda pendiente.

## Gate de evidencia primaria

P3B registra ahora fuentes oficiales candidatas de forma separada a los datasets. La fuente CNE descubierta en `gob.pe` permanece:

```text
source_class = OFFICIAL_PRIMARY_CANDIDATE
pin_status = DISCOVERED_UNPINNED
expected_sha256 = null
```

No se promueve ningún valor solo por conocer una URL oficial ni por calcular el SHA-256 de una copia local no fijada.

El proceso es obligatoriamente de dos etapas:

1. **fijar la fuente primaria**: obtener una copia oficial reproducible y registrar `pin_status = PINNED` + `expected_sha256` por revisión versionada;
2. **verificar el dataset**: la copia usada debe tener exactamente ese SHA-256 y luego contrastarse tabla/página por tabla/página.

Mientras la fuente siga `DISCOVERED_UNPINNED`, no puede existir `PRIMARY_EVIDENCE_READY_FOR_REVIEW` ni `ELIGIBLE_FOR_PRIMARY_DATASET_PR`.

Después del pin, el flujo exige:

1. copia local cuyo SHA-256 coincida exactamente con `expected_sha256`;
2. tablas verificadas;
3. referencias de página/sección;
4. revisor identificado;
5. confirmación de comparación manual;
6. evaluación de elegibilidad;
7. **nueva revisión del dataset por PR + CI**.

El mejor resultado previo al PR es `ELIGIBLE_FOR_PRIMARY_DATASET_PR`. No existe promoción automática y ese estado mantiene `professional_emission=false`.

Además, el loader del catálogo aplica `validar_dataset_record()` y cruza cualquier `PRIMARY_VERIFIED` con `ampacity_primary_sources.json`. Exige fuente existente, oficial candidata, `PINNED`, hash idéntico, misma referencia normativa, páginas y registro de revisión. Una edición manual inconsistente hace fallar la carga y CI.

Detalle del proceso: `docs/P3B_EVIDENCIA_PRIMARIA.md`.

## Binding P3B → Ib/In/Iz

P3B ya puede transportar un factor resuelto hasta el cálculo P3 sin convertirlo en un simple número anónimo. `ampacity_factor_binding.py` genera una entrada de factor que conserva:

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

Ejemplo de desarrollo con el dataset actual:

```text
Iz_base = 296 A
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

Un futuro conjunto de factores podrá reportar `automatic_normative_lookup=true` únicamente si **todos** los factores aplicados provienen de datasets P3B primarios/verificados y ninguno es manual o secundario. Ese indicador no cambia por sí solo la madurez global P3 ni habilita emisión mientras el módulo continúe `UNDER_VALIDATION`.

## Benchmark reproducible

`examples/run_benchmarks_p3b.py` genera:

`benchmark_p3b.json`

CI exige:

- `failed = 0`;
- `pass = true`;
- `evidence_level = SECONDARY`;
- `professional_emission = false`.

Esto evita que un benchmark verde se interprete erróneamente como validación normativa primaria.

## Siguiente paso P3B

1. obtener/archivar una copia primaria reproducible para los subconjuntos CNE a automatizar;
2. fijar su SHA-256 oficial mediante una revisión versionada independiente;
3. verificar que la copia de trabajo coincida byte a byte con ese pin;
4. realizar comparación independiente de páginas/tablas;
5. crear por PR una nueva revisión primaria del dataset, nunca mutar la secundaria en runtime;
6. cargar datasets primarios pequeños por eje (temperatura, agrupamiento y, cuando aplique, suelo);
7. comparar contra casos manuales independientes;
8. usar el binding P3B → P3 ya implementado con datasets primarios reales;
9. construir el gate formal de salida P3;
10. elevar madurez solo si la evidencia lo permite.
