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
| Dinámica de motor y arranque SCR | OpenModelica + Modelica Standard Library | Adaptador MCP experimental disponible para equivalente RL explícito: DOL y SCR de una máquina delta. Calificación de fabricante y traducción de redes completas pendientes. |
| Otras funciones pendientes | Por evaluar para cada estudio | Buscar y probar herramientas existentes antes de crear cálculos nuevos. |

**OpenModelica está integrado mediante `ejecutar_dinamica_modelica`.**
El contrato delimita los componentes, topologías y datos admitidos.
`contrastar_dinamica_con_modelica` conserva su función histórica de comparación
de trazas; esa comparación no sustituye la nueva ejecución de red/control.

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
reclasifican como una integración externa ya completada. El siguiente trabajo es completar calificación industrial y las funciones
habituales de OpenDSS pendientes, manteniendo las rutas físicas propias retiradas.

Arc Flash permanece diferido por instrucción del usuario.

## Actualización de ejecución y retiro — 2026-10-03

Física propia DOL/RK4 y SCR/RL retirada. El adaptador MCP experimental MSL
ejecuta DOL y SCR de una máquina delta sobre equivalente RL común. El control
SCR es el de referencia de MSL, con bypass automático; no es un dispositivo de
fabricante. SCR multimotor y conexión estrella permanecen bloqueados.
La recomendación del catálogo no habilita la traducción automática del unifilar
completo. Ver [migración](MIGRACION_MODELOS_ABIERTOS.md) y
[verificación SCR](MSL_SCR_VERIFICACION.md).
