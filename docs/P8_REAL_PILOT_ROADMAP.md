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
| P8C4B | DONE | dispositivos P5 + curva + dataset TCC numérico real |
| P8C5 | DONE | readiness integral P1/P3/P4/P5 sin ejecutar estudios |
| P8C5A | DONE | `PROJECT_DATA → P2_PROJECT` y etiqueta visual `PROYECTO P2` |
| P8D1 | DONE | ejecución controlada real P1/P3/P4; P5 queda pendiente con binding explícito |
| P8D2 | NEXT | binding explícito dispositivo → falla P4 + ejecución P5 |
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

## P8C5/P8C5A — readiness integral cerrado

P8C5 materializa una sola vez hasta la capa más alta solicitada y después inspecciona el modelo activo. No reconstruye el modelo tras P3/P5 y no ejecuta estudios.

P8C5A cerró el único blocker detectado en el primer ensamblaje integral: la ruta histórica P3 rotulaba toda base P2 no normativa como `P2_CATALOG`, aunque la asignación proviniera del expediente.

La semántica queda ahora separada:

```text
PROJECT_DATA → P2_PROJECT → PROYECTO P2
CATALOG_DATA → P2_CATALOG → CATÁLOGO P2
```

Los perfiles P3 nuevos guardan campos genéricos `assignment_*`. Para una asignación `PROJECT_DATA`, los campos `catalog_*` quedan vacíos y no contienen datos de proyecto. Los perfiles históricos de catálogo continúan siendo legibles mediante fallback compatible.

El resultado `ampacity.evaluar()` propaga el origen hasta `base_evidence`, y Workspace V3 consume esa evidencia sin recalcular ni inferir procedencia en JavaScript.

Con P8C5A, el manifiesto integral focalizado queda:

| Scope | Estado pre-P8D |
| --- | --- |
| POWER_FLOW | READY |
| VOLTAGE_DROP | READY |
| AMPACITY | READY |
| IEC60909 3F MAX/MIN | READY |
| IEC60909 1F-T MAX/MIN | READY |
| PROTECTION_TCC | READY |

El gate devuelve:

```text
readiness_status = READY_FOR_CONTROLLED_EXECUTION
all_requested_ready = true
next_gate = P8D_CONTROLLED_EXECUTION
```

Esto sigue siendo readiness: no ejecuta Solve, `ampacity.evaluar`, `calc_sc`, evaluación TCC, capacidad de corte, I²t, clearing time ni coordinación.

## P8D1 — primera ejecución controlada real

P8D1 consume el readiness P8C5 y ejecuta una secuencia fija, explícita y trazable:

1. `POWER_FLOW` — OpenDSS;
2. `VOLTAGE_DROP` — OpenDSS;
3. `AMPACITY` — P3 MCP;
4. `IEC60909_3PH_MAX_MIN` — pandapower explícito;
5. `IEC60909_1PH_GROUND_MAX_MIN` — pandapower explícito con Z0.

No existe selección automática de motor, target de falla, cross-check ni emisión profesional. Si hay varias barras de cortocircuito, todas se ejecutan y Workspace conserva el agregado; no se elige una silenciosamente.

La regresión P8D1 verifica además que `Line.R1` de OpenDSS permanece invariante desde readiness hasta 3F MAX/MIN y 1F-T MAX/MIN. El diagnóstico del piloto descartó una mutación térmica de `Line.R1`.

Un manifiesto nuevo que queda bloqueado por readiness invalida los estudios visibles de la ejecución anterior en Workspace. Esto evita que un resultado previo pueda parecer perteneciente al intento bloqueado, sin reconstruir ni modificar el modelo OpenDSS activo.

P5 queda deliberadamente fuera de P8D1. Tener dispositivo y TCC materializados no basta para saber qué corriente de P4 debe alimentar cada chequeo.

## P8D2 — siguiente gate: binding P4 → P5

P8D2 debe declarar por dispositivo, como mínimo:

- `device_id`;
- `fault_bus`;
- `fault_type` (`3ph` o `1ph-ground`);
- `case` (`max` o `min`);
- la magnitud de corriente consumida del resultado P4 (`ikss_ka`);
- procedencia y revisión/modelo del resultado P4.

El binding debe fallar cerrado si falta un dato, si la barra no fue ejecutada en P4, si el tipo/caso no coincide con el resultado seleccionado o si existen varias alternativas sin selección explícita.

P8D2 debe reutilizar el resultado P4 ya ejecutado; no debe relanzar silenciosamente otro escenario de cortocircuito. Con binding válido podrá evaluar capacidad de corte y, cuando el dataset numérico sea `TOTAL_CLEARING_TIME` y la corriente esté dentro de dominio, promover clearing time para los chequeos P5 soportados.

Se conserva la separación semántica:

- breaker: Icu para capacidad de corte; Ics/Icw solo como ratings distintos y no sustitutos;
- fuse: `breaking_capacity_ka`;
- TCC: solo dataset numérico real;
- sin `automatic_fault_binding`.

## Gate visual del piloto real

La ruta visual sigue siendo **Workspace V5**. No se crea una interfaz paralela para P8.

Antes de mostrar el primer resultado real se conservan estas reglas:

1. la identidad visual del conductor no puede sobrescribir el binding técnico P2/P3;
2. un conductor `PROJECT_DATA` se distingue de un producto `CATALOG_DATA`;
3. V3 muestra `PROYECTO P2` para base real del expediente y `CATÁLOGO P2` para biblioteca;
4. V4 conserva barra de falla, motor, caso MAX/MIN y madurez;
5. V5 solo muestra curvas TCC cuando exista dataset numérico real materializado;
6. V5 conserva Icu/Ics/Icw de breaker separadas del poder de corte de fuse;
7. ningún panel JavaScript recalcula ingeniería;
8. cada resultado debe pertenecer a la revisión vigente del modelo.

`READY_TO_BUILD_MODEL`, `MODEL_BUILT_NOT_EXECUTED`, `P3_MATERIALIZED`, `P5_TCC_MATERIALIZED_NOT_EXECUTED`, `READY_FOR_CONTROLLED_EXECUTION` y `CONTROLLED_EXECUTION_COMPLETED` son estados distintos y no se sustituyen entre sí.

```text
automatic_defaults = false
automatic_dispatch = false
automatic_fault_binding = false
crosscheck = false
professional_emission = false
```