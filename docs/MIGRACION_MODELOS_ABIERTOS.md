# Migración a modelos abiertos y cobertura industrial


**Ampliación Q5 (4 de octubre):** dos motores SCR delta sobre red RL común verificados mediante siete estudios, 50/60 Hz, cargas distintas y bypass independientes. Ver [alcance y evidencia](MSL_SCR_DOS_MOTORES.md). Más de dos SCR, mezcla DOL/SCR y estrella siguen fuera del alcance.

Actualizado: 4 de octubre de 2026. Regla del usuario: una ruta principal por
estudio; usar el motor integrado suficiente; retirar física propia duplicada.

## Cambio ejecutado

- Se eliminaron las ecuaciones del circuito T, el integrador RK4 y el
  equivalente físico SCR/RL de los módulos de ejecución propios.
- Las entradas antiguas devuelven `RETIRED_CUSTOM_BACKEND`, sin resultados y
  sin conversión automática. Los expedientes históricos siguen siendo legibles
  y sus verificadores de integridad se conservan.
- Se añadió `ejecutar_dinamica_modelica`: compila conexiones de componentes
  existentes de MSL 4.0.0 y ejecuta OpenModelica 1.27.1. El MCP comprueba datos,
  configura componentes, procesa CSV y compara criterios. No integra ecuaciones
  eléctricas ni mecánicas en Python.
- El adaptador DOL está **verificado en alcance** (DOL01–DOL03 cerrados; [evidencia](MSL_DOL_VERIFICACION.md)), con red trifásica equilibrada
  representada por un equivalente RL explícito en la barra común. No convierte
  automáticamente el circuito OpenDSS ni sus cargas de potencia constante.
- La ejecución SCR está **verificada en alcance para una o dos máquinas delta con controles genéricos MSL** (SCR01–SCR03 cerrados en Q4).
  Se resolvió el bloqueo con el solucionador algebraico `newton` de OpenModelica
  (documentado como prototipo); el integrador sigue siendo DASSL del motor externo.
  El control MSL realimenta corriente de la red cerrada y decide el bypass.
  Se verifica corriente, velocidad, par, tensión de barra/terminal y tiempos.
  Estrella, más de dos motores SCR y combinaciones DOL/SCR siguen bloqueados; no hay fallback al modelo retirado.
  Ver [alcance y evidencia](MSL_SCR_VERIFICACION.md).

## Herramientas y datos

1. `configurar_dinamica_modelica`: registrar compilador y biblioteca ya instalados.
2. `obtener_contrato_dinamica_modelica`: consultar alcance y disponibilidad.
3. `validar_dinamica_modelica`: entregar el paquete explícito.
4. `ejecutar_dinamica_modelica`: producir entradas, modelo, trazas nominales y
   refinadas, registro de ejecución, resultados y hashes en un directorio nuevo.

Ejemplos: `examples/msl_motor_dol.json`, `msl_motor_two.json`,
`msl_motor_locked_rotor.json`, `msl_motor_scr.json`,
`msl_motor_scr_unreachable.json`, `msl_motor_scr_50hz.json`, `msl_motor_two_scr.json`,
`msl_motor_two_scr_60hz.json` y `msl_motor_two_scr_loaded.json`. Son datos sintéticos;
no describen M1/M2. SCR exige además tolerancias de refinamiento de tensión,
par y tiempo de bypass explícitas.

La red requiere tensión, frecuencia, ángulo de energización y R/X por fase
referidas a la barra común. La máquina requiere conexión y parámetros SI de
fase, resistencias referidas al estator, inductancias, pares de polos,
temperatura y modelo de pérdidas. La carga requiere inercias, amortiguamiento,
curva de par y mecanismo antirretorno declarado. Sin ese mecanismo, la curva
debe cubrir también velocidades negativas; el transitorio puede invertir
brevemente el par. Se prohíbe extrapolar. No se supone un freno de la bomba.

El modelo fija resistencias y omite pérdidas de núcleo, adicionales y térmicas,
según la declaración explícita del paquete. Los contactos y triacs tienen
regularización numérica documentada en el contrato. Los criterios del ejemplo
son ilustrativos y no son mínimos normativos ni datos de fabricante.

El refinamiento reduce tolerancia, paso interno máximo y paso de salida.
Las métricas conservan los estados de ambos lados de cada evento SCR y
calculan corriente/tensión RMS por ciclo, par medio por ciclo y
velocidad. Estabilidad numérica y cumplimiento de criterios se reportan por
separado. Un motor que no acelera no se convierte en una ejecución exitosa de
diseño porque el solver haya terminado.

## Qué retiramos y qué conservamos

| Componente actual | Decisión | Razón |
|---|---|---|
| Física DOL propia: circuito T y RK4 | Retirada | MSL dispone de máquina y mecánica; adaptador DOL verificado en alcance ejecutable. |
| Física SCR/RL propia | Retirada | MSL tiene máquina, triacs y control; sustitución SCR verificada en alcance de una o dos máquinas delta y controles genéricos. |
| Comparación que volvía a calcular el surrogate SCR | Retirada | Dependía de las funciones físicas eliminadas. Se conserva el contraste histórico de trazas. |
| Admisión de datos de motores | Conservada | Evita datos faltantes, bases o supuestos silenciosos; no sustituye un solver. |
| Curvas TCC de fabricante, bandas y clearing time | Conservadas | `OCRelay` calcula actuación del relé; no equivale a todas las curvas y tiempos totales de despeje. |
| Comparación Ib/In/Iz, caída y daño I²t | Conservada | Postproceso, tablas trazables y criterios, no duplicación del solver de red. |
| Extensión IEC 2F-T propia | Conservada temporalmente | pandapower integrado no tiene contraparte directa del método/alcance; FaultStudy exploratorio no demuestra equivalencia IEC. |
| Informes, gráficos, unidades y hashes | Conservados | Son funciones de la interfaz MCP. |

## Necesidades habituales y motor principal

Esta tabla separa una capacidad de una biblioteca de un estudio MCP disponible.

| Necesidad industrial | Ruta principal | Estado MCP y trabajo pendiente |
|---|---|---|
| Flujo, caída, pérdidas y cargabilidad | OpenDSS | Disponible con alcances y datos declarados. |
| Contingencias N-1, transferencias y deslastre | OpenDSS | Disponible para escenarios estáticos explícitos; sin afirmar cobertura de contingencias no ejecutadas. |
| Cortocircuito IEC 60909 | pandapower | 3F, 2F y 1F-T max/min dentro del alcance. Aportes de máquinas y secuencias exigen sus fichas. |
| Ampacidad y protección de conductores | Tablas + resultados del motor | Disponible dentro de catálogos/métodos verificados; mantener trazabilidad normativa. |
| Coordinación TCC puntual | Curvas de fabricante + corriente de falla | Disponible con limitaciones; selectividad integral no demostrada. |
| Caída estática durante arranque | OpenDSS | Disponible con corriente y fp de arranque explícitos. |
| Aceleración DOL e interacción de motores | OpenModelica/MSL | Adaptador verificado en alcance RL común; siete casos MCP, cuatro contrastes con ejemplo original MSL. Traducción de redes completas excluida. |
| Arranque suave con SCR y bypass | OpenModelica/MSL | Verificado en alcance de una o dos máquinas delta con controles MSL, realimentación y bypass automático. Dispositivo de fabricante, estrella, más de dos SCR y combinación DOL/SCR fuera del alcance comprobado. |
| Compensación de reactiva y bancos | OpenDSS | Integración verificada en alcance estático: bancos ideales por etapas, demanda explícita, FP/tensión/pérdidas/cargabilidad y balances. [Alcance](COMPENSACION_REACTIVA_OPENDSS.md); armónicos, reactores y control automático pendientes. |
| Armónicos, THD y resonancia | OpenDSS | Prioridad de integración: espectros, fuentes armónicas, barrido y benchmarks. No inferir espectros de un fp. |
| Demanda, perfiles y operación temporal | OpenDSS | Prioridad de integración: perfiles explícitos y simulación temporal. No confundir con transitorios EMT. |
| Ajustes y actuación de relés de sobrecorriente | pandapower `OCRelay` | Adaptador pendiente; complementar datos de interruptor y clearing time cuando corresponda. |
| Variadores y estabilidad de respaldo | Primero los motores ya considerados | VFD/control específico pendientes. ANDES sólo si se demuestra falta para el alcance de estabilidad fasorial pedido. |
| Malla de tierra: paso/contacto | Motor abierto por investigar | No cubierto por representar el neutro o calcular falla a tierra. |
| Arc Flash | Diferido por el usuario | No habilitar por completar cortocircuito y TCC. |

## Orden de cierre

1. DOL01–DOL03, SCR01–SCR03 y TWO_SCR01–TWO_SCR02 cerrados: mantener ambas regresiones y los alcances del [registro de cierre](ESTADO_CIERRE_MODULOS.md). Las fichas del equipo son datos del proyecto; no recuperar física propia.
2. Bancos estáticos verificados en alcance. Ampliar armónicos y perfiles con OpenDSS, verificando cada estudio mediante MCP y referencias independientes. La ampliación no reabre el alcance estático cerrado.
3. Integrar actuación de relés con pandapower y conservar datos de clearing.
4. Completar datos/benchmarks de uso industrial, informes y mejoras visuales.
5. Investigar las carencias restantes (p. ej. malla de tierra) antes de agregar
   motores. Arc Flash sigue pendiente.

No se declara terminado el conjunto de necesidades habituales con esta primera
migración. Tampoco se instalan ANDES, VeraGrid, DPsim u OpenIPSL por figurar en
el catálogo: se mantienen como candidatos para una carencia comprobada.

## Evidencia y reproducibilidad

`scripts/verify_modelica_motor_adapter_mcp.py` comprueba retiro y bloqueo de datos
por MCP real stdio. Con `--omc` y `--msl` ejecuta tres casos sintéticos e incluye
un oráculo nodal independiente de rotor casi bloqueado, utilizado sólo para
pruebas. La CI ordinaria ejecuta los gates de admisión/retiro; no instala el
compilador y no debe confundirse con ejecución física en esa CI.

Fuentes primarias de componentes:
[MSL 4.0.0](https://github.com/modelica/ModelicaStandardLibrary/tree/v4.0.0),
[arrancador MSL](https://doc.modelica.org/Modelica%204.0.0/Resources/helpWSM/Modelica/Modelica.Electrical.PowerConverters.Examples.ACAC.SoftStarter.html),
[IndMach012](https://opendss.epri.com/IndMach012.html),
[OCRelay](https://pandapower.readthedocs.io/en/latest/protection/oc_relay.html).
