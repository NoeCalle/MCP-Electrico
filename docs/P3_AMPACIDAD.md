# P3 — Ampacidad foundation

## Estado

**UNDER_VALIDATION.**

Esta primera entrega de P3 incorpora el contrato de cálculo y trazabilidad para verificar:

```text
Ib <= In <= Iz
```

pero **no** declara todavía una implementación automática completa de IEC 60364-5-52 ni del CNE–Utilización. La foundation separa correctamente los datos y evita convertir una ampacidad de catálogo en `Iz` normativo sin justificación.

## Referencias registradas

El registro P3 incluye, como referencias versionadas:

- `IEC_60364_5_52_2009_A1_2024`: IEC 60364-5-52:2009+AMD1:2024, Ed. 3.1;
- `PERU_CNE_UTILIZACION_2006`: Código Nacional de Electricidad – Utilización, aprobado por R.M. N.° 0037-2006-MEM.

Registrar una norma **no significa** que sus tablas estén implementadas. Cada registro conserva `automatic_tables=false` hasta que el proyecto incorpore perfiles normativos versionados, evidencia de tablas/factores y benchmarks.

## Variables

### Ib — corriente de diseño

P3 acepta dos modos:

1. `EXPLICIT_DESIGN_CURRENT`: el usuario aporta `Ib` y una referencia/metodología;
2. `FLOW_CURRENT_EXPLICITLY_ACCEPTED_AS_IB`: se usa la corriente máxima resultante del flujo OpenDSS **solo después de una aceptación explícita** de que ese escenario representa la corriente de diseño.

El sistema nunca convierte automáticamente una corriente de flujo en `Ib`.

### In — corriente nominal/ajuste de protección

`In` se declara expresamente junto con su referencia. El campo visual histórico `corriente_nominal_a` del alimentador **no se interpreta como In**, porque también ha sido utilizado para representar ampacidad/rating de conductor en vistas anteriores.

### Iz base

La foundation usa como punto de partida la ampacidad trazable de una asignación P2 de conductor y conserva:

- producto/código;
- condición de instalación publicada;
- fuente del fabricante;
- ampacidad base.

Ese valor sigue identificado como **ampacidad base de catálogo**, no como `Iz` normativo final.

### Factores de corrección

Cuando se suministran factores explícitos:

```text
Iz = Iz_base * product(k_i)
```

cada factor debe contener:

- identificador;
- valor;
- referencia;
- tabla/cláusula opcional;
- condición opcional.

Además se exige `referencia_condiciones_instalacion`, que documenta por qué los factores elegidos son compatibles con la condición base de la ampacidad utilizada.

Si no se aplican factores, el usuario debe confirmar expresamente que las condiciones reales coinciden con las condiciones base publicadas y documentar esa comprobación. P3 no asume silenciosamente `product(k_i)=1`.

## Resultado

La evaluación devuelve:

- `CUMPLE`;
- `NO_CUMPLE`;
- `DATOS_INSUFICIENTES`.

Y conserva por separado:

- `Ib`;
- `In`;
- `Iz_base`;
- factor total;
- `Iz`;
- chequeo `Ib <= In`;
- chequeo `In <= Iz`;
- referencias de Ib/In/base/factores/condiciones;
- norma registrada;
- madurez `UNDER_VALIDATION`.

## Seguridad de estado

Un perfil P3 se invalida si la asignación P2 deja de coincidir con la ficha sobre la que fue creado. Se detectan al menos:

- cambio de conductor;
- cambio de condición de instalación;
- cambio de ampacidad base.

Crear un circuito nuevo también limpia los perfiles P3.

## Readiness y matriz E

La matriz de motores declara ampacidad como:

- backend preferente: `mcp`;
- implementación: disponible en foundation;
- madurez: `UNDER_VALIDATION`;
- emisión profesional automática: no habilitada.

`evaluar_preparacion_estudio("ampacidad")` comprueba un contrato específico P3 y no exige indiscriminadamente todos los datos de flujo/cortocircuito. Un perfil completo puede devolver `READY_DATA + READY_ENGINE + READY_TO_EXECUTE`, mientras `professional_emission=false` se mantiene por madurez.

## Workspace V3

La vista Ampacidad muestra resultados ya calculados por Python:

- Ib;
- In;
- Iz base;
- producto de factores;
- Iz;
- estado.

El JavaScript no calcula corrientes, factores ni criterios; únicamente controla navegación y selección del elemento.

## Qué falta para cerrar P3

La foundation **no cierra P3**. Permanecen pendientes:

1. definir el alcance normativo exacto por tipo de conductor/instalación y edición;
2. incorporar perfiles/tablas/factores normativos de forma legalmente reproducible y versionada;
3. distinguir claramente BT/MT y los ámbitos donde IEC 60364-5-52/CNE son aplicables;
4. modelar temperatura ambiente/suelo, agrupamiento, resistividad térmica y demás variables necesarias según el método seleccionado;
5. construir benchmarks manuales/independientes con resultados esperados fijados antes de ejecutar;
6. validar casos límite y combinaciones de factores;
7. definir el gate formal de salida P3;
8. solo entonces considerar `VALIDATED_WITH_LIMITATIONS`.

Hasta ese cierre, cualquier resultado P3 debe conservar visible `UNDER_VALIDATION` y `automatic_normative_lookup=false`.
