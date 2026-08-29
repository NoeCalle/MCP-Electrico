# P8 — Subroadmap del primer piloto real

Este documento descompone la fase P8 del roadmap profesional sin ampliar el alcance declarado de MCP Eléctrico 0.9 Engineering Preview.

## Regla del piloto

El objetivo no es hacer más tipos de cálculo. El objetivo es demostrar que un expediente real puede recorrer una cadena reproducible, trazable y fail-closed sin copiar datos sintéticos de P8A ni inventar valores faltantes.

```text
expediente / SLD / fichas / estudios
        ↓
P8B admisión de entradas
        ↓
P8C reconstrucción y materialización
        ↓
readiness por estudio
        ↓
ejecución controlada P1/P3/P4/P5
        ↓
Workspace V5
        ↓
P7A snapshot + P7B reconstrucción + P7C reporte
```

`professional_emission=false` durante todo P8 mientras no exista un gate posterior que la habilite legítimamente.

## Estado de subhitos

| Subhito | Estado | Resultado |
| --- | --- | --- |
| P8A | DONE | piloto integral sintético 22.9/0.48 kV |
| P8B | DONE | intake real, topología construible y gates por scope |
| P8C1 | DONE | identidad de `source.bus` real hasta OpenDSS/P2 |
| P8C2 | DONE | contrato Z0 alineado con materialización 1F-T |
| P8C3A | DONE | pandapower deja de depender de `sourcebus` literal |
| P8C3B | DONE | `manifest → OpenDSS + P2 + Z0` reproducible, sin estudios |
| P8C3C | DONE | separación `MODEL_BUILT` vs `STUDY_READY` por scope |
| P8C4A | ACTIVE | conductor real + Ib/In/Iz base + condiciones/factores P3 |
| P8C4B | NEXT | dispositivos P5 y datasets TCC numéricos reales |
| P8C5 | PENDING | readiness integral después de materializar P3/P5 |
| P8D | PENDING | primera ejecución controlada del proyecto real |
| P8E | PENDING | Workspace V5 + snapshot/reconstrucción/reporte del caso real |
| P8F | PENDING | hardening derivado de fricciones del piloto |

P6 IEEE 1584 permanece `DEFERRED` y no bloquea este recorrido.

## P8C4A — datos P3 reales

Un código de cable del proyecto no necesita existir en la biblioteca interna de fabricantes. P8C4A permite registrar una asignación `PROJECT_DATA` con:

- `element_id`;
- `conductor_code`;
- `base_ampacity_a` explícita;
- `ampacity_reference`;
- `installation_reference`;
- `norm_id` registrado;
- `ib_a` + `ib_reference`;
- `in_a` + `in_reference`;
- factores explícitos con referencia **o** `base_conditions_confirmed=true`.

El binding P3 de proyecto fija `NormAmps` para conservar la ampacidad base, pero no reemplaza R1/X1: las impedancias siguen siendo las declaradas en `topology.lines` por el expediente.

P8C4A materializa datos. No ejecuta `Ib <= In <= Iz` y no convierte materialización en cumplimiento.

## P8C4B — siguiente gate P5/TCC

P5 no se materializará desde metadata insuficiente. El siguiente bloque debe cerrar antes de crear dispositivos o curvas:

- semántica de capacidad de corte según tipo de dispositivo;
- norma/referencia explícita del equipo;
- identidad de curva;
- dataset TCC numérico, no solo metadata;
- forma `SINGLE`/`BAND`, segmentos y puntos;
- semántica de tiempo;
- procedencia/revisión;
- vínculo inequívoco dataset ↔ dispositivo.

No se digitalizan ni sintetizan curvas de fabricante automáticamente.

## Gate visual del piloto real

La ruta visual sigue siendo **Workspace V5**. No se crea una interfaz paralela para P8.

Antes de mostrar el primer resultado real deben cumplirse estas reglas:

1. la identidad visual del conductor no puede sobrescribir el binding técnico P2/P3;
2. un conductor `PROJECT_DATA` debe distinguirse visualmente de un producto `CATALOG_DATA`;
3. V3 no debe rotular una Iz base de proyecto como `CATÁLOGO P2`;
4. V4 conserva barra de falla, motor, caso MAX/MIN y madurez;
5. V5 solo muestra curvas TCC cuando exista dataset numérico real materializado;
6. ningún panel JavaScript recalcula ingeniería;
7. cada resultado debe pertenecer a la revisión vigente del modelo.

La corrección de la etiqueta de origen P3 (`P2_PROJECT` vs `P2_CATALOG`) es un gate previo a ejecutar/mostrar P3 real, no una razón para mezclar esa modificación con la materialización no ejecutante P8C4A.

## Criterio para pasar a P8D

P8D solo comienza cuando todos los scopes solicitados por el manifiesto del proyecto real estén materializados y su readiness sea explícito. `READY_TO_BUILD_MODEL`, `MODEL_BUILT_NOT_EXECUTED` y `READY_FOR_CONTROLLED_EXECUTION` son estados distintos y no se sustituyen entre sí.

```text
automatic_defaults = false
automatic_dispatch = false
crosscheck = false
professional_emission = false
```
