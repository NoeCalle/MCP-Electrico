# Contraste externo de motor y SCR

## Contra qué se compara

Se ejecutaron componentes **sin modificar** de Modelica Standard Library **4.0.0**
en **OpenModelica 1.27.1, Windows 64 bits**. La biblioteca es un modelo externo;
su motor integra estados eléctricos, par electromagnético y movimiento. Los
tiristores son interruptores ideales con resistencia/conductancia finitas y
extinción por corriente. No son una ficha ni una prueba de un fabricante.

Fuentes primarias:

- [Ejemplo publicado SoftStarter](https://doc.modelica.org/Modelica%204.0.0/Resources/helpWSM/Modelica/Modelica.Electrical.PowerConverters.Examples.ACAC.SoftStarter.html).
- [Fuente exacta de la biblioteca 4.0.0](https://github.com/modelica/ModelicaStandardLibrary/tree/v4.0.0).
- [OpenModelica para Windows](https://openmodelica.org/download/download-windows/).

Primero se ejecutó el ejemplo publicado hasta 5 s. Después se crearon wrappers
propios de conexión y parámetros: **no se presenta el ejemplo publicado como si
tuviera los parámetros de nuestro motor**. La máquina del contraste usa la
representación eléctrica `Electrical.Machines.BasicMachines...IM_SquirrelCage`;
el ejemplo publicado usa `Magnetic.FundamentalWave...IM_SquirrelCage`.

## Caso común, explícitamente sintético

Fixture `MCP-REF-DYNAMIC-RMS-01`, **no M1/M2 de la estación de bombeo**:

| Parámetro | Valor en ambos |
|---|---:|
| Tensión nominal de líneas / conexión | 480 V / delta |
| Frecuencia / pares de polos | 60 Hz / 2 |
| Rs / Rr por fase, referido al estator | 0.07 / 0.10 ohm |
| Lsigma estator / rotor | 0.0008 / 0.0008 H |
| Lmagnetización | 0.008 H |
| Inercia motor / carga | 2.5 / 7.5 kg·m² |
| Curva carga (rad/s, N·m) | (0,100), (100,300), (200,600), lineal |
| Resistencias / temperaturas | fijas a 348.15 K; coeficiente cero en MSL |
| Saturación, núcleo, pérdidas adicionales, fricción viscosa | excluidos explícitamente |
| Estado inicial | corriente/flujo cero en MSL, velocidad cero; MCP eléctrico algebraico |

El apoyo unidireccional de MSL representa el límite de velocidad no negativa
del MCP; la carga aplica la misma curva resistente. No se usa para introducir
par de aceleración adicional. El rotor conserva su inercia y los transitorios.

## Qué se reproduce y qué queda fuera

El MCP se ejecuta mediante **herramientas MCP reales por stdio** y calcula su red
fundamental. La referencia recibe la **amplitud RMS de esa fuente** y los mismos
**ángulos de disparo**, interpolados linealmente entre muestras. Sus fases se
mantienen equilibradas, con ángulos fijos. Se fuerza el bypass al tiempo del MCP
(3.45 s); no se dispara a partir de la velocidad de la referencia.

Esto es **reproducción de entradas en lazo abierto**, no validación conjunta de
red + control. Los parámetros SCR de referencia son Ron=1e-5 ohm, Goff=1e-5 S,
Vknee=0; bypass Ron=1e-6 ohm, Goff=1e-9 S. Están declarados en los wrappers.

## Resultado observado

| Al 90 % de velocidad síncrona | MCP, muestra declarada | Modelica, cruce interpolado |
|---|---:|---:|
| Arranque directo | 1.79 s | 1.807591 s |
| SCR, misma secuencia de entradas | 3.47 s | 3.752290 s |

El tiempo del MCP se publica sobre su malla; el contraste también interpola ese
cruce para separar la diferencia física de la resolución de salida.

En SCR, a 1 s, el MCP predice aproximadamente 1000 A, 492 N·m y 23.51 rad/s;
la referencia produce **894 A RMS medio de líneas, 373 N·m medio y 13.70 rad/s**.
El menor par inicial retrasa la aceleración. Más tarde, bajo los ángulos
reproducidos, la referencia alcanza aproximadamente **1232 A RMS en la línea
más cargada antes del bypass**, frente al límite declarado de 1000 A del
equivalente. Esto **no prueba un fallo de un controlador real**: su realimentación
no se ejecutó en la referencia.

Sobre los 240 ciclos completos de 4 s, la diferencia relativa L2 es:

| Magnitud | DOL | SCR |
|---|---:|---:|
| RMS medio de corrientes de línea | 2.859 % | 24.075 % |
| Par electromagnético medio | 6.669 % | 45.012 % |
| Velocidad | 0.886 % | 30.478 % |

Son diferencias de trayectorias, **no tolerancias normativas**. Incluyen el
transitorio inicial que el modelo algebraico del MCP no representa. Tampoco
son errores atribuibles al motor real del usuario.

## Precisión y evidencia

Referencia DASSL: tolerancia 1e-7, salida nominal 50 µs; repetición a 1e-9,
salida nominal 25 µs y paso interno máximo 50 µs. Los eventos interrumpen la
malla nominal; se conserva la malla real y se integra por interpolación.

Al refinar, el cambio máximo del RMS medio es menor que 0.026 A, del par medio
menor que 0.007 N·m y del cruce de velocidad menor que 2e-7 s. Las diferencias
con el MCP son mayores que estos cambios numéricos.

`contrastar_dinamica_con_modelica(directorio_evidencia)`:

1. Verifica esquema, fixture admitido, conjunto de archivos y SHA-256.
2. Verifica que la amplitud/ángulo externos reproduzcan las entradas declaradas.
3. Rechaza tiempos inversos, valores no finitos, datos insuficientes y ventanas incompletas.
4. Integra RMS por línea sobre ciclos completos de 60 Hz; conserva media y máximo.
5. Compara par medio, velocidad, llegada al objetivo y refinamiento externo.

El verificador **no certifica quién produjo una traza** ni ejecuta programas
externos. El expediente conserva los comandos, códigos de salida y mensajes
reales del simulador. No se concede PASS normativo, de dispositivo ni de diseño.

## Reproducción

Requiere el Python del proyecto, OpenModelica 1.27.1 para Windows y las fuentes
locales de MSL 4.0.0 (incluidos `ModelicaServices` y `Complex`). No se instala
Modelica como dependencia del servidor MCP.

```powershell
python scripts/verify_motor_external_candidate_mcp.py --output work/reference
python scripts/build_modelica_motor_reference.py --output work/reference --msl-root RUTA_MSL_4_0_0
```

Con `OPENMODELICAHOME` apuntando al runtime y `APPDATA` a una carpeta de trabajo,
ejecutar `omc.exe run.mos` dentro de `work/reference/published`, `DOL` y `SCR`.
El resultado de cada simulación debe contener una ruta de salida y el mensaje
`The simulation finished successfully`. El proceso de omc por sí solo puede
terminar con código cero aunque la compilación falle; revisar esos mensajes.

```powershell
python scripts/package_modelica_motor_reference.py --workspace work/reference --output work/reference-evidence --runtime RUTA_OPENMODELICA --msl-root RUTA_MSL_4_0_0
python scripts/verify_motor_external_reference_mcp.py --evidence work/reference-evidence
```

El empaquetador vuelve a ejecutar los casos y la repetición fina, recoge códigos
de salida y mensajes y crea el índice de integridad. El ejemplo publicado ya
debe haberse ejecutado. Las rutas locales del expediente no son portables como
comandos; los datos y hashes sí lo son, y los wrappers se regeneran con las
rutas de la instalación nueva.

## Estado de la ampliación

**Contraste externo ejecutado; SCR con discrepancias, sin cualificación de
dispositivo.** Queda corregir la representación trifásica y contrastar el lazo
cerrado, así como obtener datos físicos/control/protección del motor real.
El modelo RMS DOL conserva su alcance limitado. Dinámica simultánea y VFD son
extensiones separadas. Arc Flash continúa diferido.
