# P8F — Hardening posterior al primer piloto real

P8A–P8E demostraron la cadena integral del primer proyecto real. P8F no amplía tipos de cálculo: convierte esa cadena ya demostrada en una ruta de uso controlada, repetible y operable desde MCP Eléctrico 0.9 Engineering Preview.

P6 IEEE 1584 permanece `DEFERRED` y no forma parte de este cierre.

## Estado

| Subhito | Estado | Objetivo |
| --- | --- | --- |
| P8F1 | DONE | entrada MCP única `generar_dossier_piloto_real` delegando en la misma cadena P8E2 |
| P8F2 | DONE | integridad del dossier: inventario SHA-256 y verificación exacta antes de promover `DOSSIER_READY` |
| P8F3 | DONE | repetición/aislamiento: entregas independientes, collision-safe y sin sobrescritura silenciosa |
| P8F4 | DONE | first-use por MCP stdio real: ejemplo, contrato de errores y smoke `server.py` end-to-end |
| P8F5 | NEXT | gate final P8 y checklist para iniciar uso controlado con expedientes reales |

## P8F1 — entrypoint MCP integral

La admisión P8B ya estaba expuesta como tool MCP, pero P8E2 solo existía como orquestador Python. P8F1 cerró esa brecha sin crear una ruta de cálculo paralela.

La entrada pública es:

```text
generar_dossier_piloto_real(manifest, directorio_salida)
```

Su contrato obliga a reutilizar la cadena existente:

```text
manifest
  → P8D1: P8B/P8C readiness + P1/P3/P4
  → P8D2: binding explícito P4→P5 + TCC/clearing
  → P8E1: Workspace V5
  → P8E2: P7A snapshot + P7B reconstrucción + P7C reporte
```

P8F1 no importa ni invoca directamente OpenDSS, pandapower, `calc_sc`, flujo, capacidad de corte ni clearing time. La tool delega únicamente en `real_project_dossier.generar_dossier()`.

## P8F2 — integridad del dossier

P8F2 añade `dossier_integrity.json` como último artefacto del paquete. P8E2 solo puede devolver:

```text
DOSSIER_READY_ENGINEERING_PREVIEW
```

cuando el índice se construyó y `verificar_integridad_dossier_real()` devuelve:

```text
DOSSIER_INTEGRITY_VERIFIED
```

El índice usa SHA-256 y rutas relativas. Inventa el conjunto exacto de archivos del dossier, incluidos `p7a_netlist` y `p7b_reconstructed`.

Verifica:

- presencia de los artefactos obligatorios;
- conjunto exacto de archivos, sin extras silenciosos;
- tamaño y SHA-256 de cada archivo;
- hash canónico del payload del propio índice;
- rutas relativas seguras, sin `..` ni rutas absolutas;
- ausencia de symlinks;
- contexto trazable a manifest, revisión de modelo, P8D2, P7A y P7C.

El índice raíz no se incluye a sí mismo (`self_hash_included=false`) para evitar una referencia hash circular. Un archivo anidado que casualmente se llame `dossier_integrity.json` sí se considera parte del paquete.

P8F2 aporta integridad respecto del índice congelado, no autenticidad del autor. SHA-256 no sustituye firma digital, certificado, sello de tiempo confiable ni gate de emisión profesional.

## P8F3 — repetición y aislamiento cerrados

La política pública es:

```text
output_collision_policy = SUFFIX_INCREMENT
silent_overwrite = false
blocked_execution_creates_delivery_directory = false
```

Cada resultado declara:

- `requested_output_directory`;
- `output_directory` realmente usado;
- `output_directory_collision_avoided`.

Si `real_dossier` ya contiene una entrega, una nueva ejecución exitosa usa `real_dossier_2`, luego `_3`, etc. El dossier anterior no se reabre ni modifica.

Las regresiones integrales demuestran que:

- dos ejecuciones exitosas del mismo manifiesto producen dossiers distintos;
- el primer dossier permanece byte-intacto después de crear el segundo;
- cada entrega conserva su propio índice P8F2 verificable;
- el mismo manifiesto conserva el mismo `manifest_sha256`;
- no se exige que el SHA P7A sea idéntico entre corridas;
- Workspace queda ligado a la revisión de la ejecución exitosa más reciente;
- un intento posterior bloqueado no crea una nueva entrega ni altera el dossier válido previo.

`generar_dossier_piloto_real` sigue siendo el único entrypoint de ejecución.

## P8F4 — first-use operacional cerrado

P8F4 demuestra la ruta desde un **cliente MCP externo a la lógica de ingeniería**.

Se añadieron:

- `examples/p8_first_use_manifest.json`: plantilla completa y ejecutable marcada explícitamente como ejemplo;
- `examples/p8_first_use_mcp.py`: cliente SDK MCP sin imports de `mcp_electrico`, OpenDSS o pandapower;
- `obtener_contrato_p8f4_primer_uso()`: secuencia pública y contrato fail-closed de errores;
- `docs/P8F4_FIRST_USE_MCP.md`: guía para sustituir el ejemplo por datos/procedencias del expediente;
- workflow `p8f4-first-use-operational`: smoke real por stdio.

El smoke levanta `server.py` y descubre/ejecuta por protocolo:

```text
evaluar_admision_piloto_real
        ↓
generar_dossier_piloto_real
        ↓
verificar_integridad_dossier_real
```

El gate ya demostró en CI:

```text
intake_status = READY_TO_BUILD_MODEL
execution_status = DOSSIER_READY_ENGINEERING_PREVIEW
integrity_status = DOSSIER_INTEGRITY_VERIFIED
```

La ejecución completa detrás del servidor conserva P1/P3/P4/P5, Workspace V5 y P7A/P7B/P7C. El cliente no implementa una segunda ruta de cálculo.

### Contrato de errores

P8F4 distingue y documenta:

- `BLOCKED_MISSING_INPUTS`: reparar manifiesto y repetir admisión;
- `BLOCKED_BY_P8D2_EXECUTION`: reparar entradas/binding explícitos;
- `DOSSIER_ARTIFACT_GENERATION_FAILED`: no usar el directorio parcial como entrega;
- `DOSSIER_INTEGRITY_MISMATCH`: restaurar/regenerar desde una fuente controlada.

No existe reparación ni retry automáticos.

## P8F5 — siguiente frontera

P8F5 no añadirá cálculos. Será el gate final de P8 y debe responder una pregunta de producto: **¿está MCP Eléctrico listo para iniciar uso controlado con un expediente real bajo Engineering Preview?**

El cierre debe comprobar al menos:

- P8A–P8F4 cerrados y documentados;
- entrypoint público único y smoke MCP stdio verde;
- P8F2/P8F3 vigentes;
- Workspace V5 y dossier P7 verificables;
- lista explícita de datos que el usuario debe aportar antes de una corrida real;
- límites y módulos experimentales visibles;
- P6 `DEFERRED` no bloqueante;
- `professional_emission=false`.

## Políticas invariantes

```text
automatic_defaults = false
automatic_dispatch = false
automatic_fault_binding = false
crosscheck = false
professional_emission = false
```

## Fricciones reales endurecidas por P8F

1. un intento bloqueado nunca deja estudios previos aparentando vigencia;
2. ningún runtime intermedio puede mutar silenciosamente parámetros eléctricos del modelo;
3. P4→P5 continúa siendo un binding explícito y verificable;
4. Workspace solo presenta resultados de la revisión vigente;
5. P7B permanece aislado del proceso principal;
6. un dossier parcial no se promociona como listo;
7. los artefactos se verifican por contenido y procedencia;
8. repetir el flujo no sobrescribe silenciosamente una entrega anterior;
9. la ruta pública MCP es la misma cadena probada en CI;
10. el primer uso por protocolo ya no depende de imports internos.

## Criterio de salida de P8F

P8F se considerará cerrado cuando P8F5 confirme que un usuario puede entregar un manifiesto real completo al servidor MCP y obtener, mediante una única tool controlada, un resultado Engineering Preview con:

- ejecución P1/P3/P4/P5 trazable;
- Workspace V5;
- dossier P7A/P7B/P7C verificable;
- artefactos íntegros y no sobrescritos;
- estado del proceso principal preservado;
- errores fail-closed legibles;
- ninguna selección automática de motor, falla, caso o protección;
- `professional_emission=false`.
