# P8F — Hardening posterior al primer piloto real

P8A–P8E demostraron la cadena integral del piloto. P8F no añadió tipos de cálculo: convirtió esa cadena en una ruta pública, íntegra, repetible y operable desde MCP Eléctrico 0.9 Engineering Preview.

P6 IEEE 1584 permanece `DEFERRED` y no bloquea este cierre.

## Estado final

| Subhito | Estado | Resultado |
| --- | --- | --- |
| P8F1 | DONE | entrada MCP única `generar_dossier_piloto_real` sobre la misma cadena P8E2 |
| P8F2 | DONE | `dossier_integrity.json`, SHA-256 portable y conjunto exacto antes de `DOSSIER_READY` |
| P8F3 | DONE | repetición collision-safe, entregas independientes y sin sobrescritura silenciosa |
| P8F4 | DONE | first-use por MCP stdio real contra `server.py`, con ejemplo y contrato de errores |
| P8F5 | DONE | gate ejecutable para iniciar uso real controlado + checklist de datos/procedencias |

```text
P8F = CLOSED
next_activity = FIRST_CONTROLLED_REAL_PROJECT
allowed_use = CONTROLLED_REAL_PROJECT_ENGINEERING_PREVIEW
professional_emission = false
```

## P8F1 — entrypoint público único

La ruta de ejecución real es:

```text
generar_dossier_piloto_real(manifest, directorio_salida)
```

No implementa una segunda ingeniería. Delega en P8E2 y conserva P8D1/P8D2 como fronteras obligatorias.

```text
manifest
  → P8B/P8C readiness
  → P8D1 P1/P3/P4
  → P8D2 binding explícito P4→P5 + TCC/clearing
  → P8E1 Workspace V5
  → P8E2 P7A/P7B/P7C
```

## P8F2 — integridad de entrega

P8E2 solo puede promover:

```text
DOSSIER_READY_ENGINEERING_PREVIEW
```

si `dossier_integrity.json` verifica:

```text
DOSSIER_INTEGRITY_VERIFIED
```

La verificación cubre:

- artefactos obligatorios;
- conjunto exacto de archivos;
- tamaño + SHA-256 por archivo;
- netlist P7A y reconstrucción P7B;
- rutas relativas portables;
- rechazo de rutas inseguras y symlinks;
- contexto de manifest, revisión, P8D2, P7A y P7C.

SHA-256 demuestra integridad respecto del índice congelado, no autoría. No sustituye firma digital, certificado ni emisión profesional.

## P8F3 — repetición y aislamiento

```text
output_collision_policy = SUFFIX_INCREMENT
silent_overwrite = false
blocked_execution_creates_delivery_directory = false
```

Si `dossier` ya existe, la nueva entrega usa `dossier_2`, luego `_3`, etc. El dossier previo permanece byte-intacto y verificable. Un intento posterior bloqueado no crea una entrega nueva ni modifica la ya congelada.

## P8F4 — first-use por protocolo MCP

El cliente `examples/p8_first_use_mcp.py` usa el SDK MCP y levanta `server.py` por stdio. No importa `mcp_electrico`, OpenDSS, pandapower ni P8E2.

Secuencia pública probada:

```text
evaluar_admision_piloto_real
        ↓
generar_dossier_piloto_real
        ↓
verificar_integridad_dossier_real
```

Estados de éxito:

```text
READY_TO_BUILD_MODEL
DOSSIER_READY_ENGINEERING_PREVIEW
DOSSIER_INTEGRITY_VERIFIED
```

`examples/p8_first_use_manifest.json` es una plantilla ejecutable de demostración. Sus valores `EJEMPLO P8F4` deben sustituirse por datos y procedencias del expediente real.

Guía: `docs/P8F4_FIRST_USE_MCP.md`.

## P8F5 — gate final de uso real controlado

La tool:

```text
evaluar_cierre_p8f5_uso_real_controlado()
```

comprueba contratos ejecutables, no estados escritos a mano. El gate se rompe si cambia de forma insegura cualquiera de estas fronteras:

1. P7D deja de estar listo como Engineering Preview;
2. P8B deja de ser admisión read-only/fail-closed;
3. se abre auto-dispatch, auto fault-binding o cross-check;
4. P8E2 deja de ser el orquestador del entrypoint público;
5. P8F2 deja de ser obligatorio antes de READY;
6. P8F3 permite sobrescritura o mutación de entregas previas;
7. P8F4 deja de declarar la secuencia pública por MCP stdio;
8. Workspace V5 deja de ser la ruta visual P8D2 vigente;
9. P6 entra implícitamente o se abre `professional_emission`.

Con los contratos actuales devuelve:

```text
phase_status = READY_FOR_CONTROLLED_REAL_PROJECT_USE
p8_closed = true
controlled_real_project_use_ready = true
product_release = MCP_ELECTRICO_0_9_ENGINEERING_PREVIEW
allowed_use = CONTROLLED_REAL_PROJECT_ENGINEERING_PREVIEW
next_activity = FIRST_CONTROLLED_REAL_PROJECT
```

La segunda tool P8F5 es:

```text
obtener_checklist_p8f5_datos_proyecto_real()
```

El checklist detallado se mantiene en `docs/P8_CONTROLLED_REAL_USE_CHECKLIST.md`.

## Límites que siguen cerrados

```text
automatic_defaults = false
automatic_dispatch = false
automatic_fault_binding = false
crosscheck = false
professional_report = false
professional_emission = false
```

Además:

- OpenDSS sigue siendo el motor por defecto;
- pandapower se usa explícitamente para IEC 60909 dentro del alcance validado con limitaciones;
- `iec60909_full_conformance_claim=false`;
- P6 IEEE 1584 sigue `DEFERRED`;
- Workspace V5 es visual/read-only respecto de los resultados calculados;
- la revisión humana de ingeniería sigue siendo obligatoria antes de usar conclusiones en un entregable profesional.

## Resultado de P8F

P8F cerró las fricciones observadas en el piloto:

- estado stale fail-closed;
- mutación silenciosa de parámetros bloqueada por regresiones;
- binding P4→P5 explícito;
- Workspace ligado a revisión vigente;
- P7B aislado;
- dossier parcial no promovible;
- integridad verificable;
- entregas no sobrescritas;
- ruta MCP pública probada end-to-end;
- checklist real y gate de uso controlado disponibles como tools.

P8F5 no convierte el producto en una herramienta de emisión profesional. Convierte el piloto en una **ruta de uso real controlado dentro de Engineering Preview**.
