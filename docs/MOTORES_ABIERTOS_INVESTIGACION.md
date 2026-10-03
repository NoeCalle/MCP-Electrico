# Motores y modelos abiertos para MCP Eléctrico

Investigación: **2 de octubre de 2026**. Preferencias propuestas por fenómeno y
facilidad de integración; no se ha comparado el rendimiento de todos los candidatos.

**Regla posterior del usuario:** reutilizar un motor suficientemente adecuado ya
integrado. Esta investigación es un catálogo de candidatos, no un plan para
instalarlos todos. Las preferencias pendientes requieren demostrar una carencia
de las rutas existentes antes de incorporar otro motor; ver la
[regla de reutilización](ARQUITECTURA_INTEGRACION.md).

## Recomendación para la estación de bombeo

Integrar **OpenModelica + Modelica Standard Library (MSL)** primero. Ya se ejecutaron
OpenModelica 1.27.1 y MSL 4.0.0 en esta PC con un motor sintético y componentes SCR.
Falta que una herramienta MCP ejecute la red, el motor y el controlador juntos.
Los parámetros y límites del fabricante seguirán siendo necesarios para estudiar M1/M2.

OpenModelica es el simulador; MSL y OpenIPSL son bibliotecas de modelos.
ANDES, VeraGrid y DPsim son otros motores de cálculo. Seleccionar una biblioteca
compatible con el fenómeno es parte de la decisión, además de seleccionar el motor.

## Candidatos comprobados en documentación y código

| Motor / biblioteca | Modelos y fortalezas relevantes | Límites y situación en esta PC | Licencia publicada |
|---|---|---|---|
| **OpenDSS + IndMach012** | Modelo de máquina de inducción por componentes simétricas y modo Dynamics, existente en el motor que ya utilizamos. Permite dinámica electromecánica de redes de distribución. | OpenDSS instalado, pero el estudio dinámico MCP actual no utiliza IndMach012. Hay que comprobar arranque desde reposo, representación de carga mecánica y eventos en un piloto. No representa la conmutación SCR por fase. | OpenDSS BSD-style; revisar también dependencias DSS-Extensions. [Dinámica EPRI](https://opendss.epri.com/Dynamics.html), [componente](https://opendss.epri.com/IndMach012.html), [integración temporal](https://opendss.epri.com/OpenDSSDynamicsMode.html). |
| **OpenModelica + MSL** | Máquina `IM_SquirrelCage`, triacs, control de disparo y ejemplo `SoftStarter`; componentes para convertidores y control V/f. Dinámica eléctrica y mecánica por fase. | Referencias externas ya ejecutadas. Adaptador de estudios MCP pendiente. Debe configurarse la red, carga, control e inicialización; el ejemplo no es una ficha de fabricante. | MSL 4.0.0 BSD-3-Clause; runtime y dependencias tienen licencias separadas. [Fuente MSL](https://github.com/modelica/ModelicaStandardLibrary/tree/v4.0.0), [ejemplo SCR](https://doc.modelica.org/Modelica%204.0.0/Resources/helpWSM/Modelica/Modelica.Electrical.PowerConverters.Examples.ACAC.SoftStarter.html). |
| **ANDES** | Estabilidad temporal de red y autovalores; generadores `GENROU`/`GENCLS`, excitadores, gobernadores y motores `Motor3`/`Motor5`. | Candidato para dinámica fasorial de red. No representa conmutación SCR por fase. Instalación Python/conda documentada en Windows; no instalado ni ejecutado aquí. | GPL-3.0-or-later. [Proyecto](https://github.com/CURENT/andes), [motores](https://github.com/CURENT/andes/tree/master/andes/models/motor), [licencia](https://raw.githubusercontent.com/CURENT/andes/master/LICENSE). |
| **OpenModelica + OpenIPSL** | Biblioteca de dinámica fasorial de sistemas eléctricos; motor `CIM5` de jaula simple/doble y modelos de máquinas/controles. | OpenIPSL necesita un simulador. Compatibilidad con OpenModelica amplia, que debe comprobarse para cada modelo. Biblioteca no probada en esta PC; no es una alternativa de conmutación SCR. | BSD-3-Clause para la biblioteca. [Alcance y compatibilidad](https://github.com/OpenIPSL/OpenIPSL), [modelo CIM5](https://raw.githubusercontent.com/OpenIPSL/OpenIPSL/master/OpenIPSL/Electrical/Machines/PSSE/CIM5.mo). |
| **VeraGrid — antes GridCal** | Flujo continuado, contingencias y planificación. También APIs RMS en secuencia positiva y EMT en ABC; plantilla de motor de inducción EMT. | Python y distribución Windows oficiales. No instalado ni probado aquí. Hay que fijar versión, probar modelos y adaptador. Su cortocircuito general no demuestra conformidad IEC 60909. | MPL-2.0 en el repositorio consultado. [Proyecto](https://github.com/SanPen/VeraGrid), [EMT](https://veragrid.readthedocs.io/en/latest/md_source/emt_simulations.html), [motor EMT](https://veragrid.readthedocs.io/en/stable/_modules/VeraGridEngine/Templates/Emt/induction_motor_emt_template.html), [licencia actual](https://raw.githubusercontent.com/SanPen/VeraGrid/master/LICENSE.md). |
| **DPsim** | Motor C++ con API Python; EMT y fasores dinámicos, componentes de red, generadores y convertidores. | Wheels Windows x86-64 documentados para Python 3.12. La versión Windows excluye tiempo real, VILLASnode y Sundials/modelo de generador ODE. No probado aquí; no se verificó un arrancador SCR de motor listo para reutilizar. | MPL-2.0. [Proyecto](https://github.com/sogno-platform/dpsim), [Windows y limitaciones](https://dpsim.fein-aachen.org/docs/user-guide/install/), [componentes por dominio](https://dpsim.fein-aachen.org/docs/reference/model-availability/). |
| **Protecciones de pandapower** | `OCRelay` DTOC/IDMT/IDTOC y `Fuse`: funciones existentes que conviene evaluar antes de ampliar ecuaciones propias de protección. | Código presente en pandapower 3.5.4 instalado. El módulo P5 actual del MCP todavía no utiliza `OCRelay`; presencia local no equivale a adaptación probada. No cubre automáticamente selectividad integral ni curvas de fabricantes. | BSD-3-Clause. [Documentación del relé](https://pandapower.readthedocs.io/en/v3.3.3/protection/oc_relay.html), [fuente 3.5.4](https://github.com/e2nIEE/pandapower/tree/v3.5.4/pandapower/protection). |

Las páginas de desarrollo describen capacidades que pueden cambiar. Al integrar
se fijará una versión o commit y se revisarán sus licencias y dependencias.
Las afirmaciones comerciales o de validación de los proyectos no se transfieren
al MCP ni al diseño del usuario.

## Tabla determinista añadida al selector existente

| Estudio solicitado | Preferencia propuesta | Alternativas investigadas | Motivo |
|---|---|---|---|
| Dinámica de arranque directo | OpenModelica + MSL | OpenDSS/IndMach012, ANDES, OpenIPSL, VeraGrid | Componentes físicos ya ejecutados localmente. Las alternativas fasoriales requieren delimitar otro modelo. |
| Dinámica de arranque suave SCR | OpenModelica + MSL | Ninguna calificada por ahora | Triacs y control existentes; el estudio exige comportamiento por fase. |
| Dinámica simultánea de motores | OpenModelica + MSL | OpenDSS/IndMach012, ANDES, OpenIPSL | Conectar máquinas existentes a una red común; debe probarse la interacción. |
| Dinámica con variador | OpenModelica + MSL | Ninguna calificada por ahora | Componentes de máquina/convertidor disponibles; falta probar la topología y control específicos. |
| Estabilidad transitoria de red | ANDES | OpenIPSL, VeraGrid | Motor orientado a dinámica fasorial con generadores y controles. |
| Estabilidad de pequeña señal | ANDES | VeraGrid | Análisis modal del sistema dinámico. |
| Margen de carga/tensión por flujo continuado | VeraGrid | ANDES | Ruta propuesta para planificación y CPF; no implica superioridad numérica. |
| Transitorios electromagnéticos por fase | OpenModelica + MSL | DPsim, VeraGrid | Runtime local ya ejecutado; decidir componentes/paso según el fenómeno concreto. |

**Las ocho rutas son de integración pendiente.** El selector devuelve motor
preferente, `planning_only=true`, `ADAPTER_NOT_IMPLEMENTED` y
`MODULE_NOT_READY`. No permite ejecución, emisión profesional ni alternativas
por activar `permitir_experimental`. La validación de entradas aún no está
implementada: `data_evaluated=false`; no se declara que los datos sean suficientes.

Las rutas existentes de flujo → OpenDSS y cortocircuito IEC → pandapower siguen
vigentes. Armónicos y series temporales continúan propuestos para OpenDSS.
Los módulos físicos propios de dinámica se conservan como evidencia histórica;
el selector nuevo no los usa como sustitución automática.

No se añade un segundo selector: estas reglas viven en la matriz existente que
consultan `obtener_capacidades_motores`, `seleccionar_motor_estudio` y
`evaluar_preparacion_estudio`. Una solicitud genérica «dinámica» no selecciona un
motor hasta concretar el fenómeno. La capa conversacional interpreta el pedido;
la herramienta aplica reglas registradas, no inferencias libres sobre capacidad.

## Orden de integración

1. Comprobar primero el alcance de IndMach012 para dinámica fasorial DOL: aprovecha
   el backend instalado. Si el piloto cubre el estudio pedido, registrar esa ruta
   concreta; la preferencia detallada Modelica no excluye esta posibilidad.
   Adaptador MCP para OpenModelica/MSL: empezar por arranque directo, después SCR
   con red/control/bypass explícitos y, luego, interacción entre máquinas.
2. Evaluar `OCRelay` en la ampliación de protecciones.
3. Hacer un piloto ANDES cuando se pida estabilidad de generadores/red.
4. Hacer un piloto VeraGrid cuando se pida CPF o una función de planificación
   que justifique otro adaptador.
5. Mantener OpenIPSL y DPsim como alternativas por necesidad concreta.

En cada integración: ficha de entradas, versión fija, prueba local, benchmark
independiente del fenómeno, ejecución MCP real y límites claros. **Arc Flash
sigue diferido**. No se incorporaron nuevos modelos físicos propios.

## Verificación del cambio

Regresión del selector y preparación: `tests/test_engine_selection.py` y
`tests/test_study_readiness.py`. Se verifica que circuito activo y permiso
experimental no habiliten adaptadores pendientes ni promuevan suficiencia de datos.

`scripts/verify_external_engine_selection_mcp.py` consulta por MCP stdio la matriz,
las ocho preferencias/preparaciones y las rutas existentes de flujo e IEC.
Es una prueba de selección y estados: **no ejecuta los simuladores candidatos**.

Comprobación local: **64 pruebas aprobadas** del selector, preparación y contrato
del roadmap; **19 consultas MCP aprobadas**, con 146 herramientas registradas.
Se corrigió además la consulta IEC sin circuito activo para devolver datos
faltantes y motor no preparado, en lugar de una excepción.
Regresión completa local: **950 aprobadas, 1 omitida**. Las advertencias de
dependencias se conservan en el registro; no califican los motores investigados.

## Actualización de ejecución y retiro — 2026-10-02

Física propia DOL/RK4 y SCR/RL retirada. Existe un adaptador MCP experimental
MSL DOL para equivalente RL de barra común; SCR cerrado está bloqueado por
gate numérico pendiente. La recomendación de integración del catálogo no
promueve los estudios completos. Ver [migración](MIGRACION_MODELOS_ABIERTOS.md).
