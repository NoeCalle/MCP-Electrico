# P3 — Ampacidad foundation

## Estado

**UNDER_VALIDATION.**

P3 incorpora el contrato de cálculo y trazabilidad para verificar:

```text
Ib <= In <= Iz
```

pero **no** declara todavía una implementación automática completa de IEC 60364-5-52 ni del CNE–Utilización. La foundation separa correctamente los datos y evita convertir una ampacidad de catálogo en `Iz` normativo sin justificación.

P3A añade ahora un **router normativo de aplicabilidad**: puede identificar qué tabla base y qué ejes de corrección resultan aplicables dentro del alcance modelado, sin inventar ni copiar valores de tablas todavía no cargadas.

## Referencias registradas

El registro P3 incluye, como referencias versionadas:

- `IEC_60364_5_52_2009_A1_2024`: IEC 60364-5-52:2009+AMD1:2024, Ed. 3.1, publicada el 2024-11-22;
- `PERU_CNE_UTILIZACION_2006`: Código Nacional de Electricidad – Utilización, aprobado por R.M. N.° 0037-2006-MEM.

Registrar una norma **no significa** que sus tablas estén implementadas. Cada registro conserva `automatic_tables=false` hasta que el proyecto incorpore datasets numéricos con alcance, procedencia y benchmarks suficientes.

## P3A — perfiles normativos

Se registran dos perfiles separados:

- `PERU_CNE_UTIL_2006_030_004`: router de aplicabilidad para la Regla 030-004 del CNE–Utilización 2006;
- `IEC_60364_5_52_2009_A1_2024`: `REFERENCE_ONLY`; la edición 3.1 está registrada, pero sus tablas numéricas no están cargadas.

El perfil CNE modela actualmente:

- métodos E/F/G → Tabla 1;
- métodos A1/A2/B1/B2/C/D → Tabla 2;
- temperatura → Regla 030-004(8) / Tabla 5A;
- resistividad térmica del suelo para el alcance modelado de método D en ductos enterrados → Regla 030-004(9) / Tabla 5B;
- agrupamiento → Regla 030-004(1)(c), (10) / Tabla 5C y ramas que dependen de la disposición al aire;
- transición subterránea → visible dentro del alcance de 030-004(13);
- excepción 030-004(14) siempre como `MANUAL_REVIEW_REQUIRED`.

P3A **no generaliza** 030-004(13) a cualquier cambio de instalación.

Detalle completo: `docs/P3A_PERFILES_NORMATIVOS.md`.

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
- `axis` cuando existe routing P3A vinculado;
- tabla/cláusula opcional;
- condición opcional.

Además se exige `referencia_condiciones_instalacion`, que documenta por qué los factores elegidos son compatibles con la condición base de la ampacidad utilizada.

Si no se aplican factores, el usuario debe confirmar expresamente que las condiciones reales coinciden con las condiciones base publicadas y documentar esa comprobación. P3 no asume silenciosamente `product(k_i)=1`.

Cuando P3A identifica un eje requerido, ya no se permite confirmar condiciones base ni omitir el vínculo del factor con ese eje.

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
- routing P3A vinculado cuando existe;
- madurez `UNDER_VALIDATION`.

## Seguridad de estado

Un perfil P3 se invalida si la asignación P2 deja de coincidir con la ficha sobre la que fue creado. Se detectan al menos:

- cambio de conductor;
- cambio de condición de instalación;
- cambio de ampacidad base.

Crear un circuito nuevo también limpia los perfiles y routings P3/P3A.

Si el routing normativo se redefine después de crear la ficha `Ib/In/Iz`, la evaluación y el readiness vuelven a comprobar norma, ejes requeridos y revisiones manuales.

## Readiness y matriz E

La matriz de motores declara ampacidad como:

- backend preferente: `mcp`;
- implementación: disponible en foundation;
- madurez: `UNDER_VALIDATION`;
- emisión profesional automática: no habilitada.

`evaluar_preparacion_estudio("ampacidad")` comprueba un contrato específico P3 y no exige indiscriminadamente todos los datos de flujo/cortocircuito. Sin routing P3A, un perfil manual completo puede devolver `READY_DATA + READY_ENGINE + READY_TO_EXECUTE` dentro de la foundation.

Cuando existe routing P3A, el readiness también bloquea:

- parámetros normativos faltantes;
- perfil `REFERENCE_ONLY` sin dataset aplicable;
- revisión manual pendiente;
- mezcla entre referencia CNE e IEC;
- eje requerido sin factor explícito asociado;
- confirmación de condiciones base cuando el router identifica correcciones.

`professional_emission=false` se mantiene por madurez.

## Workspace V3

La vista Ampacidad muestra resultados ya calculados por Python:

- Ib;
- In;
- Iz base;
- producto de factores;
- Iz;
- estado.

P3A añade metadatos de norma/método/routing al resultado; el navegador sigue sin calcular corrientes, factores ni criterios.

## Casos patrón P3A

Los casos de routing están separados del algoritmo en:

`mcp_electrico/data/ampacity_p3a_reference_cases.json`

Cubren condiciones base, temperatura, método D con varios ejes, agrupamiento E/F/G, alcance de 030-004(13) e IEC 2024 como `REFERENCE_ONLY`.

Estos casos prueban **aplicabilidad**, no valores numéricos de tablas.

## Qué falta para cerrar P3

La foundation y P3A **no cierran P3**. Permanecen pendientes:

1. incorporar datasets numéricos de alcance y procedencia legal explícitos;
2. seleccionar ampacidad/factor por aislamiento, método, sección y configuración dentro de cada perfil soportado;
3. mantener BT/MT y ámbitos normativos claramente separados;
4. construir benchmarks manuales/independientes de valores numéricos con resultados esperados fijados antes de ejecutar;
5. validar casos límite e interpolaciones/condiciones no tabuladas según la política que se adopte;
6. definir el gate formal de salida P3;
7. solo entonces considerar `VALIDATED_WITH_LIMITATIONS`.

Hasta ese cierre, cualquier resultado P3 debe conservar visible `UNDER_VALIDATION` y `automatic_normative_lookup=false`.
