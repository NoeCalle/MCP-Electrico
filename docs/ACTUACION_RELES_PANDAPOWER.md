# Q8 - Actuacion de reles con pandapower

Revision: 16 de octubre de 2026. Motor fijado: pandapower 3.5.4, OCRelay nativo.

## Alcance comprobado

DTOC, IDMT e IDTOC con ajustes explicitos y puntos independientes de corriente RMS
primaria sostenida durante el tiempo de operacion. IDMT/IDTOC admiten las curvas
nativas standard_inverse, very_inverse, extremely_inverse y long_inverse.
Los umbrales nativos comparan corriente estrictamente mayor que pickup; la igualdad
no activa esa etapa y puede dejar activa otra etapa inferior en IDTOC.

No se calcula cortocircuito ni una secuencia de aperturas. `sc` y `pp` seleccionan
la tabla de medicion nativa, no ejecutan estudios de red. Cada rele recibe su
corriente trazable por identificador; `protected_element_reference` es una etiqueta
de trazabilidad, sin conexion automatica al unifilar. Cada caso empieza sin disparo.

## Motor existente y ajustes

La aplicacion usa `OCRelay.from_dict`, selecciona constantes mediante el metodo
nativo `_select_k_alpha`, evalua `protection_function` y aplica `status_to_net`
sobre una tabla local de interruptores. No hay ecuaciones de curva en el adaptador.
La corriente se convierte de A primarios a kA nativos; no se aplica una relacion
CT implicita ni se modela su saturacion.

El constructor de la version fijada ejecuta cortocircuito/autograding y en DTOC
manual copia I_g en I_gg. El adaptador carga ajustes mediante la deserializacion
nativa para conservar ambos umbrales explicitos, sin modificar pandapower.
Las pruebas contrastan con el constructor IDMT y con round-trip JSON nativo,
y documentan la incidencia DTOC. Cambiar de version bloquea la ejecucion hasta
recalificarla; el uso del metodo interno esta fijado y cubierto por pruebas.

Referencias primarias: [documentacion OCRelay](https://pandapower.readthedocs.io/en/latest/protection/oc_relay.html),
[codigo OCRelay 3.5.4](https://github.com/e2nIEE/pandapower/blob/v3.5.4/pandapower/protection/protection_devices/ocrelay.py).
El informe de integridad conserva hashes del adaptador y del codigo nativo instalado.

## Tiempo del rele y despeje

`relay_operating_time_s` es la demora nativa de la orden del rele.
`breaker.clearing_delay_s` debe declarar el retardo desde esa orden hasta la
extincion del arco, con fuente. Solo si ambos existen se publica su suma en
`total_clearing_time_s`. Con retardo de interruptor desconocido (`null`) se mantiene
el tiempo del rele y se marca el despeje total como no evaluable.
No disparo se representa con tiempo `null` y semantica de infinito positivo
explicita, sin producir Infinity en JSON. Los criterios de disparo y limites de
tiempo son propios del estudio: un incumplimiento no invalida el calculo numerico.

## Uso y archivos

1. Consultar `obtener_contrato_actuacion_reles` y [ejemplo sintetico](../examples/relay_operation_stage1.json).
2. Proporcionar ajustes, corrientes, fuentes, hipotesis de corriente constante,
   criterios y retardo del interruptor conocido o explicitamente desconocido.
3. Llamar `validar_actuacion_reles` y despues `ejecutar_actuacion_reles`, con un
   directorio nuevo. El selector generico exige este paquete y no ejecuta solo.

Se conservan Inputs.json, Results.json, Informe.html e Integrity.json, incluidos
intentos de ejecucion invalidos. Las entradas rechazadas no crean un estudio;
los directorios existentes no se sobrescriben. El circuito padre no se modifica.

## Evidencia y reproduccion

61 pruebas especificas, incluyendo 36 combinaciones / 432 puntos: tipos de rele,
cuatro curvas, escenarios sc/pp y retardo conocido/desconocido. Incluyen igualdad
a pickup, puntos por encima/debajo, prioridad de etapas, serializacion nativa,
varios reles, reinicio entre casos, version incorrecta y entradas bloqueadas.
El banco escalar independiente es exclusivo de pruebas, nunca un fallback.

La prueba MCP real registra 79 llamadas y 36 combinaciones / 432 puntos:
[evidencia con hashes](evidence/relay_operation_q8_mcp.json). Tolerancia temporal:
1e-9 por maximo entre 1 y el valor absoluto de referencia en segundos.

```powershell
python -m pytest tests/test_relay_operation.py -q
python scripts/verify_relay_operation_mcp.py --output relay_operation_evidence
```

La CI repite pruebas y MCP en Linux/Windows. Los casos son sinteticos de
integracion; no califican fabricante, selectividad integral, CT/VT, recierre,
protecciones direccionales/de tierra ni un proyecto real. P5 conserva su alcance
independiente; no se promocionan tiempos Q8 automaticamente a P4/P5 o Arc Flash.
