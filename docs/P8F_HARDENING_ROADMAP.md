# P8F — Hardening posterior al primer piloto real

P8A–P8E demostraron la cadena integral del primer proyecto real. P8F no amplía tipos de cálculo: convierte esa cadena ya demostrada en una ruta de uso controlada, repetible y operable desde MCP Eléctrico 0.9 Engineering Preview.

P6 IEEE 1584 permanece `DEFERRED` y no forma parte de este cierre.

## Estado

| Subhito | Estado | Objetivo |
| --- | --- | --- |
| P8F1 | DONE | entrada MCP única `generar_dossier_piloto_real` delegando en la misma cadena P8E2 |
| P8F2 | DONE | integridad del dossier: inventario SHA-256 y verificación exacta antes de promover `DOSSIER_READY` |
| P8F3 | NEXT | repetición/aislamiento: segunda ejecución limpia, sin contaminación de estado ni sobrescritura silenciosa |
| P8F4 | PENDING | first-use operacional: ejemplo de manifiesto real, contrato de errores y smoke test desde el servidor MCP |
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

Por tanto:

```text
professional_emission = false
```

permanece cerrado.

## P8F3 — siguiente frontera

P8F3 comprobará el comportamiento operacional al repetir la misma ruta integral. El objetivo no es exigir que todos los bytes entre dos corridas sean idénticos, porque las revisiones de modelo y metadatos de ejecución pueden cambiar legítimamente. El gate será más útil:

- la segunda corrida debe crear un dossier independiente y no sobrescribir el primero;
- ambos dossiers deben conservar su propio índice P8F2 verificable;
- el primer dossier debe seguir intacto después de ejecutar el segundo;
- el proceso principal debe quedar asociado únicamente a la revisión vigente de la corrida más reciente;
- un segundo intento bloqueado no debe corromper el dossier ya entregado;
- el mismo manifiesto debe conservar el mismo `manifest_sha256`;
- no se añadirá ningún tipo de cálculo nuevo.

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
