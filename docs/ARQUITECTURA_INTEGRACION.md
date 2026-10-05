# Arquitectura: integrar herramientas existentes

**Estado vigente: Q5, 4 de octubre de 2026.** Consultar el [resumen actual](ESTADO_ACTUAL.md) y el [registro de módulos](ESTADO_CIERRE_MODULOS.md).

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
| Dinámica de motor y arranque SCR | OpenModelica + Modelica Standard Library | Adaptador MCP verificado para equivalente RL explícito: DOL y SCR de una/dos máquinas delta con controles independientes. Datos y contraste de fabricante se revisan por proyecto; traducción de redes completas excluida. |
| Otras funciones pendientes | Por evaluar para cada estudio | Buscar y probar herramientas existentes antes de crear cálculos nuevos. |

**OpenModelica está integrado mediante `ejecutar_dinamica_modelica`.**
El contrato delimita los componentes, topologías y datos admitidos.
`contrastar_dinamica_con_modelica` conserva su función histórica de comparación
de trazas; esa comparación no sustituye la nueva ejecución de red/control.

## Corrección del trabajo de motores — completada

1. Física propia DOL/RK4 y SCR/RL retirada; las entradas antiguas se rechazan sin fallback.
2. Expedientes y contrastes antiguos conservados como antecedentes, no como ejecución vigente.
3. Adaptador `ejecutar_dinamica_modelica` disponible: entradas explícitas, conexiones de componentes MSL y lectura de resultados.
4. DOL01–DOL03 cerrados en Q2; SCR01–SCR03 cerrados en Q4.
5. TWO_SCR01–TWO_SCR02 cerrados en Q5: dos ramas sobre red común, controles/bypass independientes y arranque simultáneo/escalonado a 50/60 Hz.

La verificación incluye referencias originales MSL, refinamiento por estudio,
interacción red/máquinas, balances y rechazo de ejecuciones incompletas.
[Detalle DOL](MSL_DOL_VERIFICACION.md), [SCR original](MSL_SCR_REFERENCIA_ORIGINAL.md)
y [dos SCR](MSL_SCR_DOS_MOTORES.md).

El siguiente trabajo integra armónicos y perfiles con OpenDSS, actuación de
relés con pandapower y mejoras de informes/visualización. Se mantienen las
regresiones cerradas y una ruta principal por estudio.

Arc Flash permanece diferido por instrucción del usuario.

## Alcance vigente de ejecución — 2026-10-04

OpenModelica 1.27.1 y MSL 4.0.0 fijados por hashes. La ejecución usa un
equivalente RL común equilibrado, datos SI y curva mecánica explícita.
SCR admite una/dos máquinas delta y el controlador de referencia MSL.
Más de dos SCR, mezclas DOL/SCR, estrella y traducción automática del unifilar
permanecen excluidos. No se añade una física sustituta para solicitudes excluidas.
Ver [migración](MIGRACION_MODELOS_ABIERTOS.md) y [estado actual](ESTADO_ACTUAL.md).
