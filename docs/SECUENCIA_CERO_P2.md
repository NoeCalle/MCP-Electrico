# P2 — Secuencia cero explícita

## Objetivo

Incorporar datos homopolares sin inferirlos silenciosamente desde la secuencia positiva. Esta capa es una fundación de datos para fallas a tierra, IEC 60909, protección y Arc Flash; no convierte por sí sola esos estudios en validados.

## Regla principal

MCP Eléctrico **no usa multiplicadores genéricos de R1/X1 para fabricar R0/X0** y tampoco deriva Z0 únicamente desde Scc3. Un dato homopolar debe ser explícito o provenir, en una fase posterior, de una geometría/modelo físico trazable.

## Fuente equivalente

`definir_secuencia_cero_fuente(...)` recibe R0/X0 en ohmios para escenario máximo y opcionalmente mínimo.

- requiere que la red equivalente P2 positivo-secuencia exista primero;
- R0/X0 se aplican directamente a `Vsource.source` de OpenDSS;
- al cambiar de escenario max/min, solo se reaplica Z0 si ese escenario tiene datos explícitos;
- si falta Z0 del escenario activo, QA devuelve `BLOCKER`; no reutiliza silenciosamente la del otro escenario.

## Líneas

`definir_secuencia_cero_linea(...)` recibe:

- R0 [ohm/km];
- X0 [ohm/km];
- C0 [nF/km] opcional;
- referencia y URL opcionales de procedencia.

P2 v1 limita esta representación a líneas trifásicas y utiliza la definición de componentes simétricas de OpenDSS. La definición explícita de R0/X0 no reemplaza una futura representación por geometría cuando el estudio requiera conductor de neutro, pantalla, puesta a tierra o acoplamientos más detallados.

## Transformadores

El transformador se trata de manera deliberadamente distinta. Su respuesta homopolar no depende solo de un par R0/X0: intervienen el grupo vectorial, la ruta de neutro, la puesta a tierra y la estructura magnética del núcleo.

`definir_secuencia_cero_transformador(...)` registra una ficha canónica con:

- `uk0_percent`: tensión de cortocircuito de secuencia cero;
- `ur0_percent`: componente resistiva;
- relación de impedancia magnetizante de secuencia cero;
- relación R/X magnetizante;
- reparto de impedancia de fuga hacia HV;
- lado y modo de neutro cuando se declara;
- Rn/Xn cuando existe impedancia de puesta a tierra;
- procedencia.

La ficha incluye una proyección preparada para los campos de transformador de pandapower (`vk0_percent`, `vkr0_percent`, `mag0_percent`, `mag0_rx`, `si0_hv_partial`, `rn_ohm`, `xn_ohm`).

### Límite OpenDSS actual

P2 **no proyecta automáticamente esta ficha Z0 al objeto Transformer de OpenDSS**. Hacerlo como `Z0 = Z1` sería una hipótesis no documentada y puede ser incorrecto, especialmente cuando los efectos del núcleo son relevantes.

Por ello:

- ficha Z0 ausente → `QA215 BLOCKER`;
- ficha Z0 presente pero sin estrategia OpenDSS validada → `QA217 BLOCKER`;
- esto distingue falta de datos de limitación del motor/modelo.

La futura solución puede requerir, según el caso, modelo de núcleo, devanado delta/terciario equivalente, reactor adicional o utilizar la representación IEC 60909 de pandapower. La estrategia deberá benchmarkearse antes de habilitar fallas a tierra con transformadores.

## QA

Para los estudios de falla actualmente identificados por el MCP, P2 revisa:

1. red equivalente positiva documentada;
2. Z0 explícita de la fuente para el escenario activo;
3. R0/X0 de cada línea involucrada;
4. ficha profesional del transformador;
5. ficha de secuencia cero del transformador;
6. compatibilidad/proyección del motor.

Aunque los datos estén completos, `short_circuit` continúa `UNDER_VALIDATION`; esta fase no cambia su madurez ni lo convierte en IEC 60909.

## Referencias técnicas

- EPRI OpenDSS — propiedades `Vsource` R0/X0/Z0.
- EPRI OpenDSS — propiedades `Line` R0/X0/C0 y definición por componentes simétricas.
- EPRI OpenDSS — Neutral Rules y propiedades Rneut/Xneut.
- EPRI OpenDSS — Modeling Transformer Core Effects in OpenDSS.
- pandapower 3.5.4 — transformer zero-sequence parameters.
