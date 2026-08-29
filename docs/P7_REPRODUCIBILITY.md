# P7 — Expediente y reproducibilidad

## Objetivo

P7 convierte los resultados técnicos ya disponibles en un proyecto que pueda **congelarse, verificarse, reconstruirse y revisarse** sin depender de memoria de conversación, rutas temporales o capturas manuales.

P7 no cambia la madurez de P1–P5 ni habilita emisión profesional. Su finalidad inmediata es cerrar el blocker restante para **MCP Eléctrico 0.9 — Engineering Preview**.

## Roadmap P7

```text
P7A  snapshot canónico + SHA-256                DONE / EXPERIMENTAL
P7B  reconstrucción verificable del netlist     DONE / EXPERIMENTAL
P7C  resumen técnico HTML/PDF reproducible      DONE / EXPERIMENTAL
P7D  gate mínimo Engineering Preview 0.9         NEXT / ACTIVE HANDOFF

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

CI demuestra:

1. mismo estado + directorios distintos => mismo hash;
2. cambio de modelo => hash distinto;
3. tampering => `HASH_MISMATCH`;
4. no-overwrite;
5. netlist por contenido y sin ruta temporal;
6. timestamp Save Circuit canonizado sin alterar datos eléctricos;
7. P2/P3/P5 + gobernanza presentes;
8. `reproducible_project=EXPERIMENTAL`;
9. `professional_emission=false`.

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

P7B fija las rutas del ejemplo/CI antes de ejecutar OpenDSS porque `Compile/Save Circuit` puede cambiar el directorio de trabajo del proceso. Esta regresión queda cubierta explícitamente.

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

# P7C — reporte técnico reproducible

Implementación:

- `mcp_electrico.project_report`;
- `mcp_electrico.project_report_tools`;
- `validation_status.technical_report = EXPERIMENTAL`;
- `validation_status.professional_report = NOT_IMPLEMENTED`.

Schema:

```text
MCP_ELECTRICO_P7C_TECHNICAL_REPORT_V1
```

## Fuente única y determinismo

P7C no consulta el circuito activo ni vuelve a ejecutar estudios. La entrada es un snapshot P7A completo y verificable:

```text
P7A snapshot
   ↓
verificar SHA-256 = HASH_MATCH
   ↓
clasificar resultados por revisión congelada
   ↓
construir contenido técnico canónico
   ↓
report_sha256
   ↓
HTML print-ready
```

La construcción está bloqueada si el hash P7A no coincide. Un mismo snapshot debe producir exactamente:

```text
same report_data
same report_sha256
same HTML
```

El hash del reporte usa:

```text
algorithm = sha256
scope = canonical_p7c_report_data
```

## Contenido

El reporte incluye, cuando existen en el snapshot:

- circuito y revisión de modelo;
- SHA-256 P7A y SHA-256 P7C;
- estudios vigentes en la revisión congelada;
- resultados históricos/no vigentes separados explícitamente;
- datos profesionales P2;
- secuencia cero P2;
- ampacidad P3;
- protección y datasets TCC P5;
- madurez de módulos y limitaciones;
- versiones de motores;
- matriz/criterio de selección de motores;
- gate P5;
- P6 IEEE 1584 = `DEFERRED`;
- `automatic_dispatch=false`;
- `crosscheck=false`;
- `professional_emission=false`.

## HTML / PDF

P7C genera HTML determinista y apto para impresión A4. La exportación PDF en esta etapa es:

```text
pdf_export_mode = BROWSER_PRINT
native_pdf_generation = false
```

El botón `Imprimir / Guardar PDF` ejecuta únicamente:

```text
window.print()
```

El navegador no calcula, interpola ni modifica valores de ingeniería. El HTML contiene además el payload técnico canónico como `application/json` para trazabilidad, no como motor de cálculo.

La salida muestra de forma visible:

```text
NO APTO PARA EMISIÓN PROFESIONAL
engineering_preview_ready=false
professional_report=false
professional_emission=false
```

## Tools P7C

```text
obtener_contrato_reporte_p7c
exportar_reporte_tecnico_p7c
exportar_reporte_desde_archivo_p7c
```

## Evidencia CI P7C

CI debe demostrar:

1. snapshot origen `HASH_MATCH`;
2. HTML real generado;
3. mismo snapshot => mismo hash y mismo HTML;
4. tampering bloqueado antes de escribir;
5. separación current/historical por revisión;
6. marcador `NO APTO PARA EMISIÓN PROFESIONAL` visible;
7. `BROWSER_PRINT` explícito;
8. cero cálculo de ingeniería en navegador;
9. `technical_report=EXPERIMENTAL`;
10. `professional_report=NOT_IMPLEMENTED`;
11. `engineering_preview_ready=false`;
12. `professional_emission=false`.

# P7D — siguiente

P7D será el gate mínimo para **MCP Eléctrico 0.9 — Engineering Preview**. Deberá verificar como mínimo:

- P5 `READY_WITH_LIMITATIONS` y benchmark integral verde;
- P7A snapshot/hash reproducible;
- P7B reconstrucción DSS round-trip verificable;
- P7C reporte técnico reproducible;
- Workspace V5 existente y sin cálculo eléctrico JavaScript;
- limitaciones y madurez visibles;
- P6 IEEE 1584 explícitamente `DEFERRED`;
- `professional_emission=false`.

Solo P7D podrá cambiar:

```text
engineering_preview_ready = true
```

Eso habilitará uso operativo interno controlado; no habilitará emisión profesional.
