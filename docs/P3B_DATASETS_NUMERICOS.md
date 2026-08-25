# P3B — Datasets numéricos de ampacidad

## Estado

**UNDER_VALIDATION.**

P3B incorpora la infraestructura para resolver factores numéricos desde datasets versionados sin confundir **dato disponible** con **dato aprobado para emisión profesional**.

La regla principal es:

> Un valor numérico solo puede habilitar cálculo normativo automático profesional si su dataset tiene procedencia primaria/verificada y una política de uso que lo permita.

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

- `PRIMARY_VERIFIED`: contenido contrastado contra fuente primaria/versionada;
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

1. obtener/archivar una fuente primaria reproducible para los subconjuntos CNE a automatizar;
2. verificar hashes/versiones y transcripción independiente;
3. cargar datasets primarios pequeños por eje (temperatura, agrupamiento y, cuando aplique, suelo);
4. comparar contra casos manuales independientes;
5. integrar factores primarios con `Ib/In/Iz`;
6. construir el gate formal de salida P3;
7. elevar madurez solo si la evidencia lo permite.
