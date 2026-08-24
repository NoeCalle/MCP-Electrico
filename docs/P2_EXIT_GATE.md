# Gate de salida P2 — datos profesionales v1

## Propósito

La Fase P2 no se considera terminada por cantidad de archivos, equipos cargados o porque OpenDSS consiga resolver un caso. Se cierra cuando MCP Eléctrico dispone de una infraestructura profesional mínima, trazable y verificable para representar los datos que necesitarán P3–P6.

El gate separa dos conceptos:

- **estado de la fase del producto**: capacidades implementadas por MCP Eléctrico;
- **estado del modelo activo**: coherencia de un circuito concreto respecto de esas capacidades.

Por ello P2 puede estar `COMPLETE_WITH_LIMITATIONS` y, al mismo tiempo, un modelo activo puede quedar `MODEL_ISSUES` o un estudio puede quedar `MISSING_DATA`.

## Contrato P2 v1

P2 v1 exige que el producto disponga de:

1. transformador profesional de dos devanados y tres fases con kVA, tensiones, grupo vectorial, uk/%Z, separación R/X, pérdidas/taps cuando se suministren y procedencia;
2. red equivalente aguas arriba con Scc3/XR máxima y opcional mínima, escenario activo y procedencia;
3. conductor/cable trazable como producto de catálogo más condición de instalación publicada, separado de la mera anotación visual;
4. secuencia cero explícita: R0/X0 de fuente y líneas, más ficha homopolar canónica de transformador;
5. readiness por estudio: `READY_DATA`, `MISSING_DATA`, `ENGINE_NOT_READY`, `MODULE_NOT_READY`;
6. inspector V2 de fuente, transformador y cable/instalación;
7. seguridad de estado para no reutilizar datos P2, asignaciones o Z0 obsoleta;
8. checks de coherencia entre ficha profesional y modelo activo.

La tool `evaluar_cierre_p2()` devuelve estos criterios y la situación del circuito activo.

## Checks de coherencia del modelo

El gate comprueba, sin ejecutar un estudio:

- tensión de la red equivalente frente a `Vsource.source`;
- número de fases válido de líneas, transformadores, cargas y generadores;
- correspondencia de buses HV/LV del transformador;
- correspondencia de kV, kVA y conexiones de devanados con la ficha P2;
- consistencia de `NormAmps` con la asignación trazable de conductor;
- consistencia de R1/X1 cuando la biblioteca efectivamente los aplicó;
- existencia de los buses referenciados por cargas/generadores.

Un transformador legacy sin ficha P2 genera `WARNING`, no se convierte falsamente en transformador profesional. La preparación para un estudio específico sigue siendo responsabilidad de `evaluar_preparacion_estudio(...)`.

## Qué significa COMPLETE_WITH_LIMITATIONS

El cierre P2 v1 **no** significa que todos los datos eléctricos posibles estén implementados. Significa que el alcance soportado está definido y que los datos fuera de alcance se rechazan o permanecen explícitamente ausentes.

Limitaciones conservadas:

- catálogo de conductores acotado a productos trazables cargados;
- subconjunto explícito de grupos vectoriales P2 v1;
- no se deriva R0/X0 desde R1/X1 o Scc3 ni se calcula aún desde geometría física;
- la ficha Z0 de transformador no se proyecta automáticamente a OpenDSS hasta validar una estrategia que represente adecuadamente conexión, neutro y estructura magnética;
- la ampacidad de catálogo todavía no es `Iz` normativo;
- IEC 60909 sigue perteneciendo a P4;
- la representación visual de readiness específica se incorporará a las vistas de los estudios V3–V6.

## Relación con las fases siguientes

El cierre P2 habilita comenzar **P3 — ampacidad normativa**, pero no habilita automáticamente ningún modelo para emisión.

La cadena continúa:

```text
P2 datos profesionales
  ↓
P3 Ib / In / Iz + factores normativos
  ↓
P4 IEC 60909
  ↓
P5 protecciones / TCC / I²t
  ↓
P6 IEEE 1584
```

Cada fase conserva su propia matriz de madurez, benchmarks y gate de salida.
