# Pandapower engine v1

## Objetivo

Incorporar pandapower como segundo motor de cálculo accesible desde MCP Eléctrico sin reemplazar OpenDSS, sin router automático y sin cross-check entre motores en esta fase.

OpenDSS continúa siendo el motor por defecto del proyecto. Pandapower v1 se invoca explícitamente mediante la tool MCP `ejecutar_flujo_pandapower()`.

## Versión

La dependencia se restringe a `pandapower>=3.5.4,<3.6`.

## Arquitectura v1

```text
ChatGPT
   |
   v
MCP Eléctrico
   |
   +-- OpenDSS (motor por defecto)
   |
   +-- pandapower v1 (invocación explícita)
```

Pandapower v1 no mantiene un segundo modelo editado manualmente. El puente lee la topología y parámetros del modelo activo ya definido en MCP/OpenDSS, construye una red pandapower nueva en memoria y la resuelve independientemente. No utiliza resultados del flujo OpenDSS como entrada.

Esta decisión es transitoria: P2 deberá enriquecer el modelo de ingeniería para que transformadores, fuentes equivalentes, secuencias y otros datos críticos puedan convertirse de forma trazable a distintos motores.

## Alcance soportado

La primera versión acepta únicamente:

- sistema trifásico balanceado;
- un único nivel nominal de tensión;
- barra fuente `sourcebus`;
- fuente ideal de 1.0 pu y 0°;
- elementos `Line` y `Load`;
- flujo AC balanceado con Newton-Raphson;
- R1, X1 y capacitancia positiva C1 de la línea cuando está disponible;
- corriente nominal de línea solo si existe como metadato explícito del proyecto.

## Rechazos deliberados

El motor devuelve `compatible=false` y códigos `PPxxx` cuando encuentra condiciones fuera del alcance. En v1 se rechazan expresamente:

- transformadores (`PP010`);
- generadores o motores (`PP011`);
- líneas no trifásicas (`PP020`);
- cargas no trifásicas (`PP030`);
- más de un nivel nominal de tensión (`PP040`);
- ausencia de `sourcebus` (`PP002`).

El rechazo es preferible a completar silenciosamente %Z, pérdidas, grupo vectorial, datos de secuencia o cualquier otro parámetro faltante.

## Resultado

`ejecutar_flujo_pandapower()` reporta:

- versión del motor;
- madurez `EXPERIMENTAL`;
- alcance declarado;
- compatibilidad del modelo;
- convergencia;
- tensión y ángulo por bus;
- corriente por extremo de línea;
- pérdidas activas y reactivas por línea;
- pérdidas totales;
- cargabilidad únicamente cuando existe corriente nominal explícita.

El resultado se registra en el workspace como estudio `powerflow_pandapower`, pero no sustituye el `powerflow` base de OpenDSS ni cambia el `solved_revision` del modelo.

## Validación inicial

El bridge se prueba contra el solver independiente de dos barras introducido en P1. Esto valida la conversión y el flujo pandapower dentro del caso soportado sin comparar OpenDSS contra pandapower.

No existe código de cross-check en esta versión.

## Estado de madurez

`pandapower_power_flow = EXPERIMENTAL`

No debe usarse todavía como base autónoma para emisión profesional.

## Futuro

Las extensiones naturales, una vez que P2 disponga de datos profesionales, son:

1. transformadores con `vk_percent`, `vkr_percent`, pérdidas, taps y grupo vectorial trazables;
2. red equivalente externa con potencia de cortocircuito y X/R;
3. motores;
4. IEC 60909 mediante el módulo de cortocircuito de pandapower;
5. protección de sobrecorriente;
6. selección explícita de motor por estudio.

El router automático y el cross-check entre motores quedan deliberadamente fuera de esta etapa.
