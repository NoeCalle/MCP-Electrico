# Arquitectura: integrar herramientas existentes

## Decisión del usuario

MCP Eléctrico permite al usuario pedir estudios en lenguaje natural. El cliente
conversacional interpreta el pedido y llama a las herramientas MCP; el servidor
prepara las entradas y ejecuta software especializado gratuito y de código
abierto que cubra el estudio solicitado.

Antes de implementar física propia se debe buscar una solución existente y
comprobar su alcance, licencia, instalación y funcionamiento con el caso. Solo
una carencia documentada justifica proponer una implementación propia.

## Regla de reutilización de motores

Si un motor ya integrado cubre suficientemente el estudio solicitado, se reutiliza.
La existencia de otro motor abierto con la misma función no justifica instalarlo
ni mantener una segunda integración para ese estudio.

Antes de admitir otro motor se documentará la carencia concreta: fenómeno o
equipo no representado, método requerido, límite de escala o rendimiento, o
integración incompatible. Se comprobará primero si otra función o biblioteca
del motor existente cubre esa carencia. La suficiencia requiere datos admitidos,
representación física adecuada y evidencia de validación dentro del alcance.

La matriz asigna una ruta operativa principal por estudio. Las alternativas
investigadas son reservas; no implican instalaciones comprometidas ni ejecución
doble. Los contrastes puntuales de validación pueden utilizar una referencia
independiente sin crear una segunda ruta operativa permanente.

Las preferencias de rutas pendientes son propuestas revisables. En particular,
no se incorporará VeraGrid solamente para CPF si un motor ya integrado lo cubre
suficientemente; tampoco DPsim para un transitorio ya cubierto por Modelica/MSL.
ANDES se evaluará cuando exista una necesidad de estabilidad de red que no esté
suficientemente cubierta por la integración existente.

## Responsabilidades del MCP

- Exponer herramientas con entradas y resultados comprensibles.
- Revisar datos faltantes, unidades, conexiones, alcance y supuestos autorizados.
- Traducir las entradas al formato del motor y ejecutar sus herramientas.
- Registrar software/modelos utilizados, versiones, entradas y resultados.
- Interpretar estados del motor, comparar criterios declarados y presentar gráficos/informes.

Los adaptadores, conexiones entre componentes existentes, conversiones de
unidades y controles de datos son necesarios. Desarrollar un segundo modelo
físico para una función cubierta por una biblioteca existente requiere revisar
esta decisión de arquitectura.

## Situación actual y ruta de integración

| Estudio | Software existente | Situación / acción |
|---|---|---|
| Flujo de carga y operación de red | OpenDSS | Integración existente; mantener como motor principal dentro de su alcance. |
| Cortocircuito IEC 60909 | pandapower | Integración existente; revisar por separado extensiones propias y documentar cualquier carencia del motor. |
| Dinámica de motor y arranque SCR | OpenModelica + Modelica Standard Library | Modelos ya ejecutados externamente. Siguiente trabajo: exponer su ejecución como herramienta MCP. |
| Otras funciones pendientes | Por evaluar para cada estudio | Buscar y probar herramientas existentes antes de crear cálculos nuevos. |

**OpenModelica aún no es un motor de ejecución integrado en las herramientas
de estudio del MCP.** `contrastar_dinamica_con_modelica` verifica y compara
trazas ya producidas por el simulador externo. Los scripts de reproducción no
equivalen a una herramienta MCP que ejecute el estudio solicitado.

## Corrección del trabajo de motores

1. Detener la ampliación de los modelos físicos propios DOL/SCR como ruta principal.
2. Mantener los resultados y contrastes existentes como evidencia histórica y regresión.
3. Crear un adaptador de ejecución para los componentes existentes de Modelica:
   datos del usuario, conexiones, configuración, ejecución y lectura de resultados.
4. Probar arranque directo y SCR mediante llamadas MCP reales al motor externo,
   declarando los parámetros del motor, la carga y el controlador.
5. Definir cómo representar la red y verificar el estudio completo. La reproducción
   de amplitud/ángulos y el bypass impuesto de la comparación anterior no cubren
   esa integración ni la realimentación del controlador.
6. Después de verificar el reemplazo, migrar las herramientas de estudio y marcar
   la ruta propia anterior como histórica o retirarla con una transición explícita.

Los cierres y capacidades publicados describen el código existente. No se
reclasifican como una integración externa ya completada. El próximo hito es
**ejecutar el estudio con software externo mediante MCP**, con datos revisados;
no corregir o ampliar el equivalente físico propio.

Arc Flash permanece diferido por instrucción del usuario.
