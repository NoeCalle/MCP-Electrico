# P9 — Hardening final y freeze de MCP Eléctrico 0.9

Fecha de freeze: 2026-09-25.

P9 no añade nuevos tipos de cálculo. Su objetivo es cerrar la estabilidad de la
Engineering Preview 0.9 antes de introducir el primer proyecto minero controlado.

## Estado

| Subhito | Estado | Resultado |
| --- | --- | --- |
| P9A — aislamiento P7B/Windows | DONE | P7B usa un contexto independiente `dss.NewContext()`, sin proceso Python hijo ni timeout de `stdio` |
| P9B — regresión P0–P8 | DONE | suite completa y workflows de P0–P8 verdes sobre el árbol que llegó a `main` |
| P9C — repetibilidad por MCP | DONE | tres dossiers consecutivos en una única sesión MCP stdio, Linux y Windows, con integridad independiente |
| P9D — freeze 0.9 | DONE | documentación/contratos alineados y baseline 0.9 congelada para iniciar P10 |

```text
P9 = CLOSED
product_release = MCP_ELECTRICO_0_9_ENGINEERING_PREVIEW
baseline_status = FROZEN_FOR_CONTROLLED_REAL_PROJECT
next_phase = P10_CONTROLLED_REAL_PROJECT
next_project = SE-MIN-01
professional_emission = false
```

## P9A — P7B aislado sin subprocess

La reconstrucción P7B ya no depende de:

```text
MCP -> Python padre -> subprocess Python -> OpenDSS
```

La ruta vigente es:

```text
MCP -> proceso Python -> contexto DSS padre
                     -> dss.NewContext() aislado para P7B
```

El contexto aislado carga el netlist sin cambiar el directorio de trabajo global y
confirma explícitamente:

```text
isolation_mode = OPENDSS_NEW_CONTEXT
isolated_context = true
isolated_process = false
parent_dss_context_mutated = false
parent_structured_state_mutated = false
stored_results_promoted_to_current = false
```

### Round-trip de `Save Circuit`

Durante el hardening se identificó una diferencia de serialización de
DSS-Extensions/OpenDSS: al guardar de nuevo un circuito en el contexto aislado,
`Master.dss` puede omitir únicamente la línea generada:

```text
BusCoords BusCoords.dss
```

aunque `BusCoords.dss` continúe presente e idéntico. La comparación P7B ignora
solo esa referencia exacta y no los datos de coordenadas. El archivo
`BusCoords.dss` continúa comparándose por contenido, y cualquier otra diferencia
del netlist sigue bloqueando la reconstrucción.

## P9B — regresión y backend reproducible

La evidencia del cierre P9A/P9B incluyó:

```text
pytest completo: 574 passed
Windows Python 3.12 P7B/P8E2: 13 passed
MCP stdio Windows: DOSSIER_READY_ENGINEERING_PREVIEW
integridad: DOSSIER_INTEGRITY_VERIFIED
```

También se cerró una fuente de deriva de dependencias. P4 fue revisado y
benchmarkeado contra pandapower 3.5.4, por lo que la dependencia queda fijada en:

```text
pandapower==3.5.4
```

Una versión posterior no hereda automáticamente la madurez ni la evidencia de
3.5.4. Su adopción requiere una nueva revisión/regresión explícita.

## P9C — tres corridas en la misma sesión MCP

`examples/p9_stdio_repeatability.py` prueba la ruta pública real contra
`server.py` mediante MCP stdio.

Dentro de una única sesión:

1. valida admisión;
2. genera el dossier tres veces;
3. exige `OPENDSS_NEW_CONTEXT` en las tres reconstrucciones P7B;
4. verifica integridad después de cada corrida;
5. exige salidas collision-safe `dossier`, `dossier_2`, `dossier_3`;
6. vuelve a verificar el primer dossier después de la tercera corrida;
7. cierra limpiamente la sesión y el proceso stdio.

CI ejecuta esta prueba en:

```text
Ubuntu + Python 3.11
Windows + Python 3.12
```

Ambos entornos deben devolver:

```text
schema = MCP_ELECTRICO_P9C_STDIO_REPEATABILITY_V1
ok = true
completed_repetitions = 3
unique_output_directories = 3
manifest_hash_stable = true
first_delivery_reverified_after_final_run = true
clean_stdio_shutdown = true
```

## P9D — baseline congelada

El freeze conserva las fronteras vigentes:

```text
automatic_defaults = false
automatic_dispatch = false
automatic_fault_binding = false
crosscheck = false
professional_report = false
professional_emission = false
P6_IEEE1584 = DEFERRED
```

El freeze no significa certificación del software ni conformidad normativa
integral. Significa que la ruta Engineering Preview que entra a P10 tiene una
baseline reproducible, regresionada y portable en los entornos objetivo.

## Roadmap desde el freeze

| Fase | Objetivo | Estado |
| --- | --- | --- |
| P9 — Hardening final 0.9 | estabilidad, aislamiento, regresión y freeze | **CLOSED** |
| P10 — Proyecto real controlado | incorporar progresivamente SE-MIN-01 22.9/4.16/0.48 kV | **NEXT** |
| P11 — Validación de estudios | flujo, IEC 60909, Z0/fallas a tierra, cables, motores y protecciones contra referencias independientes | PLANNED |
| P12 — Expediente de ingeniería | snapshot, resultados, unifilar, tablas y reporte reproducible del caso real | PLANNED |
| P13 — Release 1.0 | gates finales, pruebas negativas, documentación y baseline de producto | PLANNED |
| P14 — IEEE 1584 | Arc Flash formal después de estabilizar la cadena anterior | DEFERRED |

## Regla de entrada a P10

P10 no debe inventar datos para completar la subestación. El manifiesto del
proyecto se alimentará únicamente con valores y procedencias cerrados en el caso
de ingeniería paralelo.

La incorporación será incremental:

```text
Design Basis / fuentes
-> Load List
-> 22.9 kV
-> 4.16 kV
-> 480 V
-> transformadores y puesta a tierra
-> alimentadores/cables
-> protecciones
-> estudios
```

Cada bloque debe pasar readiness antes de habilitar el siguiente estudio.
