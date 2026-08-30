# P8F — Hardening posterior al primer piloto real

P8A–P8E demostraron la cadena integral del primer proyecto real. P8F no amplía tipos de cálculo: convierte esa cadena ya demostrada en una ruta de uso controlada, repetible y operable desde MCP Eléctrico 0.9 Engineering Preview.

P6 IEEE 1584 permanece `DEFERRED` y no forma parte de este cierre.

## Estado

| Subhito | Estado | Objetivo |
| --- | --- | --- |
| P8F1 | IN PROGRESS | exponer una única entrada MCP para ejecutar el piloto real y generar su dossier P8E2 |
| P8F2 | PENDING | integridad del dossier: inventario/hash de artefactos y verificación cruzada antes de promover `DOSSIER_READY` |
| P8F3 | PENDING | repetición/aislamiento: segunda ejecución limpia, sin contaminación de estado ni sobrescritura silenciosa |
| P8F4 | PENDING | first-use operacional: ejemplo de manifiesto real, contrato de errores y smoke test desde el servidor MCP |
| P8F5 | PENDING | gate final P8 y checklist para iniciar uso controlado con expedientes reales |

## P8F1 — entrypoint MCP integral

La admisión P8B ya estaba expuesta como tool MCP, pero P8E2 solo existía como orquestador Python. P8F1 cierra esa brecha sin crear una ruta de cálculo paralela.

La nueva entrada pública es:

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

Se conservan cerradas estas políticas:

```text
automatic_defaults = false
automatic_dispatch = false
automatic_fault_binding = false
crosscheck = false
professional_emission = false
```

El éxito sigue siendo `DOSSIER_READY_ENGINEERING_PREVIEW`; no equivale a emisión profesional.

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
