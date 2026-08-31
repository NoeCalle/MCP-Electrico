# P8F — Hardening posterior al primer piloto real

P8A–P8E demostraron la cadena integral del primer proyecto real. P8F no amplía tipos de cálculo: convierte esa cadena ya demostrada en una ruta de uso controlada, repetible y operable desde MCP Eléctrico 0.9 Engineering Preview.

P6 IEEE 1584 permanece `DEFERRED` y no forma parte de este cierre.

## Estado

| Subhito | Estado | Objetivo |
| --- | --- | --- |
| P8F1 | DONE | entrada MCP única `generar_dossier_piloto_real` delegando en la misma cadena P8E2 |
| P8F2 | DONE | integridad del dossier: inventario SHA-256 y verificación exacta antes de promover `DOSSIER_READY` |
| P8F3 | DONE | repetición/aislamiento: entregas independientes, collision-safe y sin sobrescritura silenciosa |
| P8F4 | NEXT | first-use operacional: ejemplo de manifiesto real, contrato de errores y smoke test desde el servidor MCP |
| P8F5 | PENDING | gate final P8 y checklist para iniciar uso controlado con expedientes reales |

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

El índice usa SHA-256 y rutas relativas. Inventaría el conjunto exacto de archivos del dossier, incluidos los archivos de los directorios `p7a_netlist` y `p7b_reconstructed`.

Verifica:

- presencia de los artefactos obligatorios;
- conjunto exacto de archivos, sin extras silenciosos;
- tamaño y SHA-256 de cada archivo;
- hash canónico del payload del propio índice;
- rutas relativas seguras, sin `..` ni rutas absolutas;
- ausencia de symlinks, para que los bytes verificados residan dentro del paquete;
- contexto trazable a manifest, revisión de modelo, P8D2, P7A y P7C.

El índice raíz no se incluye a sí mismo (`self_hash_included=false`) para evitar una referencia hash circular. Un archivo anidado que casualmente se llame `dossier_integrity.json` sí se considera parte del paquete y debe estar indexado.

### Frontera de seguridad

P8F2 proporciona **integridad respecto del índice congelado**, no autenticidad del autor. SHA-256 por sí solo no sustituye una firma digital, certificado, sello de tiempo confiable ni gate de emisión profesional. Un actor capaz de reemplazar simultáneamente archivos e índice puede construir un nuevo paquete autoconsistente.

Por tanto `professional_emission=false` permanece cerrado.

## P8F3 — repetición y aislamiento cerrados

P8F3 prueba el comportamiento operacional de la misma ruta integral cuando se ejecuta repetidamente.

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
- cada entrega conserva su propio `dossier_integrity.json` P8F2 verificable;
- el mismo manifiesto conserva el mismo `manifest_sha256`;
- no se exige que el SHA P7A sea idéntico entre corridas, porque una nueva ejecución puede tener otra revisión de modelo;
- Workspace queda ligado a la revisión de la ejecución exitosa más reciente;
- si el intento posterior queda bloqueado antes de P8D2, no se crea `_2` ni se altera el dossier válido previo;
- el intento bloqueado puede limpiar los estudios lógicos actuales como conducta fail-closed, sin invalidar la entrega congelada anterior.

P8F3 no añade una segunda tool de ejecución. `generar_dossier_piloto_real` sigue siendo el único entrypoint; `obtener_contrato_p8f3_repeticion_dossier()` solo documenta su política.

## P8F4 — siguiente frontera

P8F4 convertirá la cadena ya endurecida en una experiencia de primer uso comprobable desde el servidor MCP. Debe cubrir:

- un manifiesto de ejemplo realista y completo, sin datos sintéticos ocultos ni defaults automáticos;
- guía mínima de campos y procedencias necesarias para poder construir un manifiesto desde expediente/SLD/fichas;
- contrato de estados y errores esperables del entrypoint;
- smoke test que registre las tools desde el mismo `server.py` y ejecute la ruta pública, no el módulo interno;
- verificación posterior del dossier con la tool MCP pública de P8F2;
- ninguna ampliación de cálculos y `professional_emission=false`.

## Políticas invariantes

```text
automatic_defaults = false
automatic_dispatch = false
automatic_fault_binding = false
crosscheck = false
professional_emission = false
```

## Fricciones reales que P8F debe endurecer

El primer recorrido integral dejó lecciones que ahora pasan a ser gates de producto:

1. un intento bloqueado nunca puede dejar estudios previos aparentando vigencia;
2. ningún runtime intermedio puede mutar silenciosamente parámetros eléctricos del modelo;
3. P4→P5 debe continuar siendo un binding explícito y verificable;
4. Workspace solo presenta resultados de la revisión vigente;
5. P7B debe permanecer aislado del proceso principal;
6. un dossier parcial no debe promocionarse como listo;
7. los artefactos del dossier deben poder verificarse por contenido y procedencia;
8. repetir el mismo flujo no debe sobrescribir silenciosamente una entrega anterior;
9. la ruta pública MCP debe ser la misma cadena probada en CI, no una implementación alternativa.

## Criterio de salida de P8F

P8F se considerará cerrado cuando un usuario pueda entregar un manifiesto real completo al servidor MCP y obtener, mediante una única tool controlada, un resultado Engineering Preview con:

- ejecución P1/P3/P4/P5 trazable;
- Workspace V5;
- dossier P7A/P7B/P7C verificable;
- artefactos íntegros y no sobrescritos;
- estado del proceso principal preservado;
- errores fail-closed legibles;
- ninguna selección automática de motor, falla, caso o protección;
- `professional_emission=false`.
