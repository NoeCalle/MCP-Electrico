# Bancos de capacitores y compensación reactiva

**Estado:** adaptador experimental, 2026-10-03. La física y el flujo los resuelve
OpenDSS. El MCP valida, configura etapas, lee resultados y presenta criterios.

## Alcance disponible

- Red pasiva trifásica equilibrada, una fuente Thevenin, líneas y transformadores
  de dos devanados. Cargas explícitas PQ o impedancia constante.
- Bancos ideales estrella a tierra o delta, hasta 8 bancos y 16 etapas por banco.
  Cada etapa corresponde a un objeto `Capacitor` nativo independiente; se conserva
  su potencia nominal aunque las etapas sean desiguales.
- Hasta 32 escenarios explícitos. El multiplicador aplica a P y Q de las cargas.
  Cada caso se compara con todos los bancos desconectados **a esa misma demanda**.
- Factor de potencia y sentido inductivo/capacitivo en el terminal externo de
  la fuente, tensiones por fase, corrientes, cargabilidad, pérdidas de líneas y
  transformadores, aporte real de cada banco y balances P/Q.
- Recomendación por demanda: menor kvar nominal conectado entre las
  configuraciones ensayadas que cumplen todos los criterios. No es una
  optimización de todas las combinaciones ni una estimación de ahorro tarifario.

El aporte real del capacitor varía con la tensión. La tensión nominal del banco
puede diferir de la barra. La potencia de la fuente se mide en su terminal externo;
las pérdidas internas del equivalente Thevenin no se suman a pérdidas de planta.

## Herramientas y datos

1. `obtener_contrato_compensacion_reactiva`: alcance y exclusiones.
2. `validar_compensacion_reactiva(paquete_estudio)`: sin resolver electricidad.
3. `ejecutar_compensacion_reactiva(paquete_estudio, directorio_salida)`: contexto
   OpenDSS aislado y carpeta nueva, sin sobrescribir evidencia previa.

Ver [paquete completo de referencia](../examples/reactive_compensation_stage1.json).
Todos los parámetros, ratings y criterios deben ser explícitos y tener procedencia.
El paquete exige aceptación experimental. El selector determinista elige OpenDSS
para `compensacion_reactiva` / `bancos_capacitores`, pero no declara listo un caso
sin pasar el validador específico.

Se declaran frecuencia, tensión/ángulo/fuerza de fuente, impedancias y capacitancia
de líneas, corriente admisible, ficha completa de transformadores, modelo/conexión
y límites Vminpu/Vmaxpu de cargas, conexión/tensión/kvar de etapas, estados 0/1,
demanda, límites de aceptación y tolerancias del solver/balance.

Las cargas PQ fuera de Vminpu/Vmaxpu pueden cambiar de representación en OpenDSS;
se registran y no se aceptan como representación PQ cumplida. Una no convergencia
se informa como **no evaluable**, nunca como prueba de sobrecarga. La sobrecarga
requiere medición válida y rating explícito. Finalizar el cálculo no significa
cumplir criterios ni autorizar emisión profesional.

## Evidencia y contraste

- 28 pruebas específicas: admisión, aislamiento de modelo/estado/medidores,
  sobrecompensación, ratings, no convergencia y archivos de integridad.
- 12 circuitos de referencia: estrella/delta, 50/60 Hz y fuente 0,9/1,0/1,1 pu.
  Cada uno compara antes/después con solución cerrada de circuito equilibrado
  de impedancia constante: 24 comparaciones de P, Q, tensión, corriente,
  pérdidas y kvar real. El oráculo está en un archivo **solo de pruebas**, no
  se importa ni ejecuta como motor operativo del MCP.
- 22 llamadas MCP stdio reales en
  `scripts/verify_reactive_compensation_mcp.py`; referencias, caso con
  transformador, etapas, sobrecarga, rechazo de datos y no convergencia.
- Gate de CI en el workflow principal; las pruebas no acreditan fabricante,
  comportamiento armónico ni todo el universo de redes OpenDSS.

Ejemplo ilustrativo, no diseño de cliente: FP 0,90177 sin banco → 0,97150 con
100 kvar nominales, con aporte real de 97,73 kvar. A demanda 0,2 pu, 50 kvar
dan FP 0,99983 pero Q = −1,571 kvar: no cumple el criterio declarado de
evitar operación adelantada. El objetivo FP ≥ 0,95 y los límites de tensión
del ejemplo son criterios ilustrativos, **no mínimos normativos universales**.

## Archivos entregados

`Inputs.json`, `Execution.json`, `Results.json`, `Informe.html`, `Integrity.json`.
Se guardan entradas, comandos de etapas/opciones, versión de motor, resultados,
balances y hashes de archivos/adaptador/dependencias. El informe muestra la
comparación por caso y enlaza los datos por elemento. El modelo padre se conserva.

## Pendientes

Armónicos, resonancia, reactores de rechazo, transitorios de conmutación,
`CapControl` automático, redes desbalanceadas, generación y selección integral
de capacitores/protecciones permanecen fuera de alcance. La siguiente integración
prioritaria es armónicos/resonancia con OpenDSS y espectros explícitos.

## Fuentes primarias del componente

Las propiedades de potencia, tensión, conexión y estados se apoyan en la
[documentación DSS-Extensions de Capacitor](https://dss-extensions.org/dss-format/Capacitor.html)
y el [componente de EPRI](https://opendss.epri.com/CapacitorObject.html).
Estas fuentes documentan el motor; no fijan criterios de aceptación del cliente.
