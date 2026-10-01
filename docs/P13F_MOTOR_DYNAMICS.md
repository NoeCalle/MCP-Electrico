# P13F — Preparación de dinámica avanzada de motores

## Estado y entregable P13F1

**P13F1: preparación de entradas físicas completa. Backend dinámico pendiente de calificación.**

El 2026-09-30 se reactivó P13F por decisión del usuario. Esta primera entrega
añade contrato SI, admisión conservadora, fixture sintético, referencias
analíticas independientes y tres herramientas MCP. La admisión prepara datos
para calificar un backend; `ready_for_execution=false` en todos los casos.

| Paso | Estado | Gate de cierre |
| --- | --- | --- |
| P13F1 — Entradas y plan | DONE | contrato explícito, rechazos reproducibles, referencias analíticas y acceso MCP sin modificar el padre |
| P13F2 — Calificación de backend | NEXT | versiones fijadas, unidades/bases, conexión, inicialización y ley de carga demostradas con benchmarks independientes |
| P13F3 — Acoplamiento con red | PENDING | resolución aislada, reemplazo explícito de carga de marcha, energía y convergencia temporal verificadas |
| P13F4 — Estudios dinámicos | PENDING | trayectorias I/V/T/velocidad, aceleración, stall y criterios del proyecto; fallo del solver explícito |
| P13F5 — Workspace y dossier | PENDING | trayectorias calculadas en Python, replay, versiones y SHA-256 trazables |

P13A–P13E conservan sus estudios estáticos, perfiles, secuencias y dossier.

## Herramientas públicas

- `obtener_contrato_dinamica_motores()` publica alcance, campos y bloqueos.
- `validar_datos_dinamica_motores(manifest, paquete_dinamico)` devuelve `data_ready`, issues con ruta/código y el paquete admitido por copia.
- `obtener_plan_validacion_dinamica_motores()` publica candidatos, referencias analíticas y pruebas pendientes.

El estado admisible es `READY_FOR_DYNAMIC_BACKEND_QUALIFICATION`.
Una entrada incompleta produce `BLOCKED_DYNAMIC_INPUTS` y `accepted_package=null`.
No existe una herramienta de ejecución dinámica en P13F1.

## Alcance inicial

`BALANCED_THREE_PHASE_SQUIRREL_CAGE_DOL`: motor de inducción de jaula,
trifásico equilibrado, arranque directo, inicialmente desenergizado y en reposo.
La interpretación electromagnética de energización se fijará en P13F2 según
el backend. Quedan pendientes VFD, soft starter, estrella-delta con conmutación,
EMT desequilibrado, saturación, evolución térmica y secuencias dinámicas multi-motor.

El paquete se vincula a un manifiesto P13A admitido mediante `project_id`
y SHA-256 del JSON canónico UTF-8: claves ordenadas, `ensure_ascii=false`,
separadores `(',', ':')`, `allow_nan=false`. Un cambio del manifiesto exige
renovar el vínculo. Las referencias a motores son insensibles a mayúsculas.

### Bases, datos y unidades

| Grupo | Datos obligatorios | Interpretación |
| --- | --- | --- |
| Manifiesto P13 | red, bus, tensión nominal, conexión, motor y carga de marcha | se reutilizan identidades; no se deducen parámetros físicos desde corriente/PF de arranque |
| Eléctrico | pares de polos, frecuencia, Rs/Rr, Lσs/Lσr/Lm | Ω/H por fase, rotor referido al estator; frecuencia igual a red; pares de polos enteros 1..64 |
| Temperaturas | estator y rotor en K | resistencias a las temperaturas de operación declaradas; temperaturas fijas |
| Pérdidas | saturación lineal, hierro y pérdidas adicionales excluidas explícitamente | hipótesis obligatorias y visibles; modelo de pérdidas limitado |
| Mecánico | Jmotor, Jcarga, amortiguamiento B | kg·m² y N·m·s/rad referidos al eje del motor; carga ya referida mediante cualquier transmisión |
| Carga | puntos velocidad/par resistente | rad/s y N·m no negativos; desde cero hasta velocidad síncrona; interpolación lineal declarada, extrapolación bloqueada |
| Inicial | modo y velocidad | `DEENERGIZED_AT_REST`, velocidad explícita cero |
| Tiempo | duración, paso y límite | segundos, malla fija integral, hasta 200000 pasos |
| Objetivos | fracción de velocidad síncrona, tiempo máximo, tensión mínima | criterios del proyecto; no constituyen resultados alcanzados |
| Procedencia | referencias de cada grupo | texto obligatorio; no autentica fabricante ni demuestra calibración |

Rs, Rr, las tres inductancias y Jmotor son positivos y finitos. Jcarga y B
admiten cero explícito. Booleanos, cadenas numéricas, NaN e infinito se rechazan.
Campos desconocidos se rechazan para impedir unidades o claims de backend
introducidos silenciosamente.

`2πf/p` es una conversión cinemática de velocidad síncrona. La admisión no
calcula corriente, torque electromagnético, aceleración, tensión ni integración.
El horizonte cubre el tiempo máximo declarado. La fracción objetivo está entre
cero y uno; la tensión mínima es positiva y como máximo 1 pu.

## Fixture controlado

`examples/p13_motor_dynamics_reference.json` se vincula a
`examples/p13_motor_starting_multi_stage3.json` y prepara `Motor.m01`.
Los otros motores permanecen como cargas de marcha declaradas en la red base;
su tratamiento deberá verificarse antes del acoplamiento P13F3.

Los valores sintéticos están marcados `CONTROLLED_REFERENCE_DATA`.
No provienen de fabricante ni se ajustaron para reproducir el arranque P13B.
Su admisión demuestra integridad del contrato y referencias. La consistencia
del circuito equivalente con datos nominales y de arranque es un gate P13F2.

## Plan de calificación independiente

El plan usa `Jtotal·dω/dt = Te − Tcarga − Bω`. Incluye dos oráculos mecánicos
analíticos a 0, 0.5, 1 y 2 segundos: soluciones cerradas de casos sintéticos,
sin integrador numérico ni backend probado.

| Caso | Referencia | Tolerancias absolutas propuestas |
| --- | --- | --- |
| B01 — Par neto constante | J=10, Te=80, Tcarga=20, B=0; ω=6t, θ=3t², Ecin=180t² | velocidad/ángulo 1e-6; energía 1e-5 |
| B02 — Amortiguamiento viscoso | J=10, Te=50, Tcarga=10, B=2; ω=20(1−exp(−0.2t)), θ=20t−100(1−exp(−0.2t)) | velocidad/ángulo 1e-6 |
| B03 — Rotor bloqueado | circuito equivalente independiente: I, PF y par con conexión y bases explícitas | valores/tolerancias pendientes |
| B04 — Balance de energía | entrada eléctrica = variación magnética/cinética + pérdidas + trabajo en eje | balance/tolerancias pendientes |
| B05 — Refinamiento temporal | dt, dt/2 y dt/4: velocidad, I, T, V y tiempo de aceleración | tolerancias por observable pendientes |
| B06 — Stall/no convergencia | objetivo inalcanzable e integración fallida explícitos | fixture/criterio pendientes |
| B07 — Aislamiento/replay | padre intacto y trayectorias repetibles con versiones exactas | proyección/tolerancias pendientes |

Valores y tolerancias pendientes deben fijarse antes de aprobar un backend.
B01/B02 no validan por sí solos el motor eléctrico. En P13F1,
`backend_benchmarks_run=false`, candidatos `NOT_QUALIFIED` y `selected_backend=null`.

## Candidatos y fuentes primarias

- [OpenDSS IndMach012](https://dss-extensions.org/dss-format/IndMach012.html)
  documenta parámetros eléctricos en pu y constantes mecánicas H/D.
  Requiere mapear SI→pu, bases, conexión, inicialización y ley de carga;
  sus defaults no reemplazan campos faltantes del contrato.
- [Modelica IM_SquirrelCage](https://doc.modelica.org/Modelica%204.0.0/Resources/helpWSM/Modelica/Modelica.Electrical.Machines.BasicMachines.InductionMachines.IM_SquirrelCage.html)
  documenta parámetros del motor de inducción. Requiere runtime/biblioteca
  fijados, acoplamiento aislado y correspondencia de pérdidas.
- [Modelica Inertia](https://doc.modelica.org/Modelica%204.0.0/Resources/helpWSM/Modelica/Modelica.Mechanics.Rotational.Components.Inertia.html)
  documenta inercia rotacional en kg·m² como referencia mecánica.

Las fuentes preparan la evaluación; no seleccionan ni califican un backend.

## Verificación y fronteras

`tests/test_p13f_dynamic_preparation.py` cubre datos faltantes, vínculo SHA,
unidades/dominio, malla temporal, criterios, referencias analíticas y
conservación del contexto DSS/Workspace. CI P13F1 lo ejecuta en Linux/Python
3.11 y Windows/Python 3.12. `scripts/verify_local_mcp.py` llama las tres
herramientas mediante stdio/HTTP, guarda `dynamic_preparation.json` y verifica
que la preparación conserva el padre.

```text
ready_for_execution = false
backend_implemented = false
dynamic_integration_performed = false
electrical_calculation_performed = false
automatic_defaults = false
automatic_dispatch = false
professional_emission = false
```
