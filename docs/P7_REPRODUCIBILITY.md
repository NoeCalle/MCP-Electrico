# P7 — Expediente y reproducibilidad

## Objetivo

P7 convierte los resultados técnicos ya disponibles en un proyecto que pueda **congelarse, verificarse, reconstruirse y revisarse** sin depender de memoria de conversación, rutas temporales o capturas manuales.

P7 no cambia la madurez de P1–P5 ni habilita emisión profesional. Su finalidad inmediata es cerrar el blocker restante para **MCP Eléctrico 0.9 — Engineering Preview**.

## Roadmap P7

```text
P7A  snapshot canónico + SHA-256                DONE / EXPERIMENTAL
P7B  reconstrucción verificable del netlist     ACTIVE / EXPERIMENTAL
P7C  resumen técnico HTML/PDF reproducible      NEXT AFTER P7B
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

El snapshot congela:

- netlist OpenDSS por `file.name` + `file.content`;
- revisión y estado del workspace;
- P2 profesional y secuencia cero;
- P3 ampacidad;
- P5 protección y datasets TCC;
- estudios registrados como evidencia;
- matriz de validación y limitaciones;
- gate P5;
- selección y versiones de motores;
- `automatic_dispatch=false`;
- `crosscheck=false`;
- `professional_emission=false`.

## Hash determinista

P7A usa:

```text
algorithm = sha256
scope = canonical_payload_without_export_paths_or_transient_timestamps
```

El JSON canónico usa claves ordenadas, separadores compactos y `allow_nan=false`.

Se excluyen únicamente datos transitorios que no representan un cambio de ingeniería:

```text
last_update
recorded_at
rutas temporales de Save Circuit
timestamp automático del comentario "Last saved by ..." de Master.dss
```

AltDSS/DSS C-API inserta ese timestamp en `Master.dss`. P7A conserva la versión/revisión del motor y todo el contenido eléctrico, sustituyendo solo el instante final por:

```text
<P7A_TRANSIENT_TIMESTAMP_REMOVED>
```

No se eliminan comentarios DSS genéricamente ni se normalizan valores eléctricos.

Dos exportaciones consecutivas del mismo estado producen el mismo SHA-256; un cambio del modelo, datos estructurados, estudios o gobernanza incluidos modifica el hash.

## Verificación y política de archivos

`verificar_snapshot_proyecto_p7a()` devuelve `HASH_MATCH` o `HASH_MISMATCH` sin reconstruir el modelo.

`exportar_snapshot_proyecto_p7a()` nunca sobrescribe una exportación previa:

```text
project.json
project_2.json
project_3.json
```

Tools P7A:

```text
construir_snapshot_proyecto_p7a
exportar_snapshot_proyecto_p7a
verificar_snapshot_proyecto_p7a
```

CI ya demuestra:

1. mismo estado + directorios distintos => mismo hash;
2. cambio de modelo => hash distinto;
3. tampering => `HASH_MISMATCH`;
4. no-overwrite;
5. netlist por contenido y sin ruta temporal;
6. timestamp Save Circuit canonizado sin alterar datos eléctricos;
7. P2/P3/P5 + gobernanza presentes;
8. `reproducible_project=EXPERIMENTAL`;
9. `professional_report=NOT_IMPLEMENTED`;
10. `engineering_preview_ready=false`;
11. `professional_emission=false`.

# P7B — reconstrucción verificable del netlist

Implementación:

- `mcp_electrico.project_reconstruction`;
- `mcp_electrico.project_reconstruction_tools`;
- `validation_status.project_reconstruction = EXPERIMENTAL`.

Schema:

```text
MCP_ELECTRICO_P7B_RECONSTRUCTION_V1
```

## Secuencia fail-closed

P7B aplica este orden:

```text
verificar SHA-256 P7A
        ↓
validar netlist y nombres DSS
        ↓
materializar en directorio nuevo
        ↓
Compile Master.dss
        ↓
limpiar estados MCP heredados
        ↓
Save Circuit nuevamente
        ↓
canonización P7A
        ↓
comparación archivo por archivo
```

### Integridad antes de escribir

Si el hash P7A no coincide:

```text
status = BLOCKED_SNAPSHOT_INTEGRITY
write_performed = false
compile_performed = false
```

El circuito activo previo permanece intacto.

### Seguridad de archivos

P7B-v1 acepta únicamente nombres `.dss` planos. Bloquea:

- rutas absolutas;
- `..`;
- `/` o `\` dentro del nombre;
- nombres duplicados sin distinguir mayúsculas/minúsculas;
- `file_count` inconsistente;
- ausencia de `Master.dss`.

La validación ocurre antes de crear el directorio destino.

### Round-trip fuerte

Después de `Compile`, P7B vuelve a ejecutar `Save Circuit` sobre el modelo reconstruido y usa exactamente la misma canonización P7A.

Solo declara:

```text
RESTORED_VERIFIED
```

si el netlist canónico completo coincide archivo por archivo.

Si existe una diferencia:

```text
status = RECONSTRUCTION_ROUNDTRIP_MISMATCH
netlist = RESTORED_MISMATCH_CLEARED
```

y el circuito no verificado se limpia para que no quede disponible accidentalmente.

## Estados que NO se restauran automáticamente

El netlist OpenDSS y los estados estructurados MCP se tratan por separado.

P7B-v1 deja explícitamente:

```text
professional_p2   = NOT_RESTORED_REQUIRES_REBIND
zero_sequence_p2  = NOT_RESTORED_REQUIRES_REBIND
ampacity_p3       = NOT_RESTORED_REQUIRES_REBIND
protection_p5     = NOT_RESTORED_REQUIRES_REBIND
tcc_datasets_p5   = NOT_RESTORED_REQUIRES_REBIND
workspace_visual  = NOT_RESTORED
studies           = NOT_RESTORED_REQUIRES_RECALCULATION
```

Por tanto:

```text
stored_results_promoted_to_current = false
```

Un estudio almacenado en P7A es evidencia histórica del snapshot; no vuelve a ser vigente solo porque el modelo DSS pueda reconstruirse.

## Tools P7B

```text
obtener_contrato_reconstruccion_p7b
reconstruir_snapshot_proyecto_p7b
reconstruir_archivo_proyecto_p7b
```

## Gate P7B

Para cerrar P7B CI debe demostrar al menos:

1. hash válido obligatorio antes de escribir;
2. round-trip canónico real `true`;
3. tampering bloqueado sin tocar el circuito previo;
4. path traversal bloqueado antes de escribir;
5. master ausente/inconsistente bloqueado;
6. mismatch de round-trip limpiado;
7. estudios históricos no promovidos;
8. `project_reconstruction=EXPERIMENTAL`;
9. `professional_report=NOT_IMPLEMENTED`;
10. `engineering_preview_ready=false`;
11. `professional_emission=false`.

# P7C — siguiente

P7C deberá convertir el snapshot verificable en un **resumen técnico reproducible HTML/PDF** consumiendo únicamente datos ya preparados por Python/MCP.

Como mínimo deberá incluir:

- identificación del proyecto y hash P7A;
- revisión del modelo;
- motores/versiones usados;
- fuentes y procedencia;
- resultados vigentes claramente separados de resultados obsoletos/no recalculados;
- estado de madurez de cada módulo;
- warnings y limitaciones;
- unifilar/workspace apto para impresión;
- P3, P4 y P5 cuando existan resultados vigentes;
- `professional_emission=false`.

P7C no debe recalcular ingeniería en HTML/JavaScript y reutilizará el mismo workspace visual.
