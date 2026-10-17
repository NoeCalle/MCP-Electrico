# Falla terminal de motor e integral térmica por fase — Q13A

Primera ruta EMT para estudiar el aporte transitorio de un motor de inducción
y su energía térmica. El solver operativo es OpenModelica 1.27.1 con
`IM_SquirrelCage` de MSL 4.0.0; el MCP configura componentes e integra las
corrientes emitidas. La referencia matemática independiente vive solo en
scripts de validación. No se ejecutan dos motores operativos para un estudio.

## Alcance explícito

Un motor estrella trifásico, simétrico, con velocidad mecánica **impuesta**.
Se energiza desde una fuente sinusoidal ideal mediante una resistencia de
contacto declarada. En el instante solicitado se desconecta la fuente y se
cortocircuitan los tres terminales con la misma resistencia explícita por fase.
Los devanados comienzan sin corriente; la velocidad está impuesta desde t=0.
El estado previo a la falla se obtiene simulando desde esa condición inicial;
no se presupone que haya alcanzado régimen permanente.

El componente MSL calcula campos/corrientes y su decaimiento. Una fuente
mecánica ideal mantiene la velocidad: **no se calcula la desaceleración libre**.
La inercia está declarada, pero con esa frontera su aceleración es cero. Esta
idealización necesita justificación para usarla como aproximación de un equipo
real durante una falla corta. No representa automáticamente la fábrica Brno.

Las resistencias corresponden a la temperatura declarada y permanecen fijas
(`alpha20s=alpha20r=0`). Sin pérdidas de núcleo, adicionales, fricción ni
evolución térmica. No se modelan delta, varias máquinas, generadores, VFD,
red de planta, maniobras sucesivas ni una protección que determine el despeje.

## Entradas y herramientas

- `configurar_falla_terminal_motor_modelica(ruta_omc, directorio_msl)` registra
  la versión real 1.27.1 y hashes del compilador/biblioteca, sin modificar DOL/SCR.
- `validar_falla_terminal_motor_modelica(paquete_estudio)` comprueba el
  contrato, parámetros SI, procedencia, presupuesto y runtime instalado.
- `ejecutar_falla_terminal_motor_modelica(paquete_estudio, directorio_salida)`
  compila MSL, ejecuta nominal/refinado y conserva entradas, fuentes, trazas,
  logs, hashes y resultados. Una falla de compilación, traza o convergencia
  deja `results=null`.

La [plantilla de prueba](../examples/qualification/motor_terminal_fault_emt.json)
contiene valores de MSL y fronteras sintéticas declaradas. No es una ficha
de placa de un motor industrial. Usa el runtime configurado para falla terminal; si no se ha seleccionado uno,
admite el runtime DOL/SCR existente de la misma versión. El adaptador DOL/SCR previo permanece intacto.

El modelo no admite campos adicionales que amplíen silenciosamente el alcance.
Se exigen referencias, 50/60 Hz, resistencia de contacto/falla positiva,
dos ciclos antes/después, al menos 500 muestras/ciclo y refinamiento de paso y
tolerancia. No se extrapola una traza incompleta ni se usa un valor por defecto.

## Magnitudes calculadas

Por cada fase de línea:

\[
J_k=\int_{t_f}^{t_e}i_k(t)^2\,dt,\qquad
I_{eq,k}=\sqrt{J_k/(t_e-t_f)}.
\]

Se incluyen las componentes presentes en la señal instantánea, incluida la
componente aperiódica. Se conserva cada fase y el máximo de sus equivalentes;
no se usa la media trifásica como corriente del conductor más exigido.
No se sustituye esta integral por `Ik''² × tiempo` ni se infiere un tiempo de
despeje. `t_e` es el final explícito del intervalo de observación de la falla.

El MCP integra exactamente el cuadrado de la interpolación lineal entre
muestras. Un integrador continuo nativo MSL integra el cuadrado dentro de la
simulación. Se contrastan ambas integrales y las ejecuciones nominal/refinada;
las comprobaciones deben cumplir la tolerancia explícita para publicar resultados.
Una traza con huecos, orden incorrecto, NaN o final incompleto se rechaza.

Estos resultados son equivalentes térmicos de la simulación EMT definida.
**No se promocionan a Ith IEC 60909**, corriente de corte, selectividad ni
aceptación de conductor/equipo. El tiempo térmico no valida el interruptor.

## Referencia independiente y pruebas

`scripts/motor_fault_thermal_reference.py` usa dos corrientes complejas de
devanado y las matrices de inductancia/resistencia de una máquina lineal a
velocidad impuesta. La solución por exponencial matricial incluye el arranque
eléctrico desde corriente cero y el cambio de fuente a cortocircuito. SciPy
integra su corriente al cuadrado por cuadratura adaptativa. No llama al
constructor MSL ni al procesador de trazas del MCP.

La suite compara formas de onda e integral por fase para 50 Hz/0°, 50 Hz/37°
y 60 Hz/0°, con velocidad 98% de la síncrona y límites prefijados de 0,1%.
También contrasta el postproceso con integrales analíticas lineales, sinusoidales
y exponenciales, prueba datos malformados y conserva el bloqueo SC3 IEC.
El workflow ejecuta el circuito nativo en Linux con la imagen oficial del
compilador fijada por digest;
Linux/Windows ejecutan las pruebas del contrato. El alcance del compilador
nativo no se presenta como validado en Windows sin su ejecución correspondiente.

## Corrección de frecuencia en la ruta IEC existente

La auditoría de `pandapower 3.5.4`, `shortcircuit/currents.py::_calc_ith`, encontró
`f=50` y `n=1` internos. Antes, en una red de 60 Hz el factor térmico empleaba
50 Hz. En el alcance existente sin máquinas se conserva el solver y se adapta
solo el argumento usado por ese factor:

\[
T_{backend}=T_{declarado}\,f_{red}/50.
\]

La fórmula del backend depende únicamente de `f × T`; esta conversión restaura
ese producto. El tiempo declarado en el expediente permanece intacto y se
expone el tiempo transformado en `thermal_backend_projection`. No representa
un cambio del tiempo de operación de la protección. En ese backend, `tk_s`
solo interviene en `_calc_ith`; no se altera el cálculo inicial ni de pico.
Se admite esta adaptación únicamente para la versión fijada y 50/60 Hz.
Una versión distinta falla cerrada para evitar aplicar dos veces una corrección
si el proveedor modifica su implementación.

Las pruebas también detectaron que `Frequency` en `New Circuit` de OpenDSS
solo fijaba la propiedad de la fuente, mientras la solución podía conservar
60 Hz al solicitar 50 Hz. La creación ahora fija explícitamente la frecuencia
base de los nuevos elementos y la frecuencia efectiva de solución. Se comprueba
la alternancia 50/60 Hz y la base de una línea añadida después.

Doce casos contrastan 3F/2F, 50/60 Hz y tres duraciones con cuadratura de la
energía AC constante + DC exponencial. Una comprobación adicional verifica
los supuestos del código del proveedor. **Esto no habilita decaimiento de
máquinas en pandapower:** el bloqueo SC3 sigue vigente.

Fuentes primarias:

- MSL 4.0.0: https://github.com/modelica/ModelicaStandardLibrary/tree/v4.0.0
- Máquina: https://github.com/modelica/ModelicaStandardLibrary/blob/v4.0.0/Modelica/Electrical/Machines/BasicMachines/InductionMachines/IM_SquirrelCage.mo
- Documentación térmica del proveedor: https://pandapower.readthedocs.io/en/stable/shortcircuit/ith.html
- Código de la versión fijada: `pandapower/shortcircuit/currents.py` de 3.5.4,
  comprobado en el runtime y en CI; la página `stable` puede cambiar.

La validación de una instalación real completa sigue abierta. Este avance
construye una ruta reproducible para un fenómeno antes excluido; aún faltan
red y máquinas completas, velocidades libres, curvas/ajustes y revisión común.
