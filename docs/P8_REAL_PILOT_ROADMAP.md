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
| P8C4A | DONE | conductor real + Ib/In/Iz base + condiciones/factores P3 |
| P8C4B | ACTIVE | dispositivos P5 + curva + dataset TCC numérico real |
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

## P8C4B — dispositivos P5 y TCC numérico

P8C4B materializa P5A/P5B solo cuando el manifiesto contiene datos suficientes para construir el objeto de protección y la curva numérica sin inferencias.

### Dispositivos

La semántica de capacidad de corte depende del tipo:

- `circuit_breaker`: Icu obligatoria; Ics/Icw opcionales y separadas;
- `fuse`: `breaking_capacity_ka` obligatorio; Icu/Ics/Icw no aplican.

Mientras P8B conserve su campo histórico genérico, un breaker puede declarar también `breaking_capacity_ka` **únicamente como alias legacy explícito igual a Icu**. El materializador P5 no lo usa como rating del interruptor.

Cada dispositivo conserva además:

- In y Ue;
- norma/referencia explícita;
- fabricante/serie/modelo cuando existen;
- ajustes Ir/Isd/Ii solo si están declarados en amperios y con procedencia;
- identidad y procedencia de curva.

Cuando existe una ficha P3 del mismo `Line.*`, In P5 debe coincidir exactamente con In P3.

### TCC

Metadata de curva no equivale a dataset ejecutable. P8C4B exige:

- `curve_id` y `dataset_id`;
- vínculo inequívoco dataset ↔ curve ↔ device;
- `shape=SINGLE|BAND`;
- semántica de tiempo;
- tipo y referencia de fuente;
- al menos un segmento;
- ID explícito por segmento;
- al menos dos puntos por segmento;
- corrientes estrictamente crecientes;
- tiempos positivos;
- `time_min_s <= time_max_s` en bandas;
- dominios de segmentos sin solaparse ni tocarse.

Una curva `MANUFACTURER_DIGITIZED` requiere además método de digitalización explícito.

P8C4B no evalúa la curva, no interpola tiempos de un caso de falla y no ejecuta capacidad de corte, I²t, clearing time ni coordinación. Solo deja los objetos P5A/P5B materializados y verificables.

No se digitalizan ni sintetizan curvas de fabricante automáticamente.

## Gate visual del piloto real

La ruta visual sigue siendo **Workspace V5**. No se crea una interfaz paralela para P8.

Antes de mostrar el primer resultado real deben cumplirse estas reglas:

1. la identidad visual del conductor no puede sobrescribir el binding técnico P2/P3;
2. un conductor `PROJECT_DATA` debe distinguirse visualmente de un producto `CATALOG_DATA`;
3. V3 no debe rotular una Iz base de proyecto como `CATÁLOGO P2`;
4. V4 conserva barra de falla, motor, caso MAX/MIN y madurez;
5. V5 solo muestra curvas TCC cuando exista dataset numérico real materializado;
6. V5 debe conservar Icu/Ics/Icw de breaker separadas del poder de corte de fuse;
7. ningún panel JavaScript recalcula ingeniería;
8. cada resultado debe pertenecer a la revisión vigente del modelo.

La corrección de la etiqueta de origen P3 (`P2_PROJECT` vs `P2_CATALOG`) es un gate previo a ejecutar/mostrar P3 real, no una razón para mezclar esa modificación con la materialización no ejecutante P8C4A/P8C4B.

## Criterio para pasar a P8D

P8D solo comienza cuando todos los scopes solicitados por el manifiesto del proyecto real estén materializados y su readiness sea explícito. `READY_TO_BUILD_MODEL`, `MODEL_BUILT_NOT_EXECUTED`, `P3_MATERIALIZED`, `P5_TCC_MATERIALIZED_NOT_EXECUTED` y `READY_FOR_CONTROLLED_EXECUTION` son estados distintos y no se sustituyen entre sí.

```text
automatic_defaults = false
automatic_dispatch = false
crosscheck = false
professional_emission = false
```
