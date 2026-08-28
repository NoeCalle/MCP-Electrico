# P7 — Expediente y reproducibilidad

## Objetivo

P7 convierte los resultados técnicos ya disponibles en un proyecto que pueda **congelarse, verificarse, reconstruirse y revisarse** sin depender de memoria de conversación, rutas temporales o capturas manuales.

P7 no cambia la madurez de P1–P5 ni habilita emisión profesional. Su finalidad inmediata es cerrar el blocker restante para **MCP Eléctrico 0.9 — Engineering Preview**.

## Roadmap P7

```text
P7A  snapshot canónico + SHA-256                ACTIVE / EXPERIMENTAL
P7B  importación y reconstrucción verificable   NEXT
P7C  resumen técnico HTML/PDF reproducible      PENDING
P7D  gate mínimo Engineering Preview 0.9         PENDING

P6 IEEE 1584 = DEFERRED
professional_emission = false
engineering_preview_ready = false
```

# P7A — snapshot canónico del proyecto

Implementación:

- `mcp_electrico.project_snapshot`;
- `mcp_electrico.project_snapshot_tools`;
- `validation_status.reproducible_project = EXPERIMENTAL`.

Schema:

```text
MCP_ELECTRICO_P7A_PROJECT_SNAPSHOT_V1
```

## Contenido congelado

El snapshot incluye:

### Modelo eléctrico

El circuito OpenDSS se exporta a DSS y se guarda en el JSON por:

```text
file.name
file.content
```

Las rutas locales no forman parte del snapshot canónico.

### Revisión del workspace

Se preservan:

- `model_revision`;
- `visual_revision`;
- modelo estructurado del workspace;
- registro de estudios y su validez respecto de la revisión;
- configuración visual relevante.

### Datos de ingeniería

Se incluyen snapshots estructurados de:

```text
P2 professional_data
P2 zero_sequence
P3 ampacity
P5 protection_data
P5 numeric TCC datasets
```

### Gobernanza

Se incluyen:

- matriz de validación;
- limitaciones declaradas por módulo;
- gate P5;
- matriz de selección de motores;
- versiones runtime disponibles;
- `automatic_dispatch=false`;
- `crosscheck=false`;
- `professional_emission=false`.

## Hash determinista

P7A usa:

```text
algorithm = sha256
scope = canonical_payload_without_export_paths_or_transient_timestamps
```

El JSON canónico usado para el digest aplica:

```text
sort_keys = true
separators = compact
allow_nan = false
```

Se excluyen del contenido hasheado únicamente datos transitorios que impedirían reproducibilidad sin representar un cambio de ingeniería:

```text
last_update
recorded_at
rutas del directorio temporal de Save Circuit
```

Por ello, dos exportaciones consecutivas del **mismo estado de ingeniería** deben producir el mismo SHA-256 aunque usen directorios temporales distintos.

Un cambio del modelo, de los datos estructurados, de un estudio registrado o de la gobernanza incluida debe modificar el hash.

## Verificación

`verificar_snapshot_proyecto_p7a()` recalcula el SHA-256 del payload y devuelve:

```text
HASH_MATCH
```

o:

```text
HASH_MISMATCH
```

Esta verificación **no reconstruye** ni ejecuta el proyecto. La reconstrucción pertenece a P7B.

## Política de archivos

`exportar_snapshot_proyecto_p7a()` no sobrescribe una exportación previa.

Ejemplo:

```text
project.json
project_2.json
project_3.json
```

La ruta de salida se devuelve como conveniencia operacional pero no forma parte del hash del contenido.

## Tools públicas P7A

```text
construir_snapshot_proyecto_p7a
exportar_snapshot_proyecto_p7a
verificar_snapshot_proyecto_p7a
```

No existe todavía una tool `importar` o `reconstruir` en P7A.

## Gate P7A

P7A puede considerarse cerrado cuando CI demuestre al menos:

1. mismo estado + directorios distintos => mismo hash;
2. cambio de modelo => hash distinto;
3. tampering del JSON => `HASH_MISMATCH`;
4. exportación no sobrescribe el archivo previo;
5. netlist guardado por contenido y sin ruta temporal;
6. P2/P3/P5 + gobernanza presentes;
7. `reproducible_project=EXPERIMENTAL`;
8. `professional_report=NOT_IMPLEMENTED`;
9. `engineering_preview_ready=false`;
10. `professional_emission=false`.

## Lo que P7A todavía no afirma

```text
reconstruction_import = NOT_IMPLEMENTED_P7A
professional_report   = NOT_IMPLEMENTED_P7A
engineering_preview_ready = false
professional_emission = false
```

P7A es un **checkpoint verificable del estado estudiado**, no un expediente profesional firmado.

# P7B — siguiente

P7B deberá demostrar que un snapshot P7A puede reconstruirse sin completar datos silenciosamente.

Como mínimo deberá:

- verificar hash antes de importar;
- reconstruir el netlist DSS desde `name/content`;
- cargar un circuito nuevo aislado del anterior;
- restaurar estados estructurados que sean técnicamente restaurables;
- distinguir datos restaurados de resultados que deben recalcularse;
- verificar que el modelo reconstruido produzca un snapshot equivalente dentro de un alcance canónico definido;
- fallar cerrado si faltan archivos, cambia el schema o el hash no coincide.

No se asumirán resultados eléctricos antiguos como vigentes solo porque existan en el JSON.