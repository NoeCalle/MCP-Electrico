# Guía práctica de capacidades verificadas

Actualización: 22 de octubre de 2026. Esta guía resume los contratos publicados;
no amplía la madurez del [registro de módulos](ESTADO_CIERRE_MODULOS.md).

## Qué verificamos como MCP

Las pruebas de los motores son la base. Nuestro cierre verifica traducción de
entradas y unidades, conexiones y bases, selección de una ruta por estudio,
opciones del motor, tratamiento de errores, interpretación de salidas y
reproducibilidad. Los contrastes independientes comprueban esas fronteras;
no pretenden recalificar toda la física de cada solver.

Una integración verificada no depende de completar todos los datos de Brno.
Un dato faltante bloquea el estudio que lo necesita. Los supuestos declarados
permiten pruebas de sensibilidad identificadas, sin convertirlas en mediciones
ni en condiciones confirmadas de la planta.

## Qué ejecutar y qué aportar

| Estudio | Motor / componente | Entradas que debe revisar el ingeniero | Evidencia y límite principal |
|---|---|---|---|
| Flujo, tensiones, pérdidas y cargabilidad | OpenDSS | Topología/fases, tensiones, impedancias, transformadores/taps, demanda y modelo de carga; ratings para cargabilidad | [Q11](CALIFICACION_TRANSFORMADORES_Q11.md), [alimentadores externos](CALIFICACION_ALIMENTADORES_EXTERNOS.md). Brno: 269 barras comparadas; semántica de carga aún bajo investigación |
| Contingencias y transferencia | OpenDSS | Estados y maniobras, fuentes alternativas, cargas críticas y criterios explícitos | [P12](P12_OPERATING_SCENARIOS.md). Análisis estático; sin selección automática de contingencias |
| Cortocircuito 3F inicial MAX o MIN | pandapower | Fuente Scc/XR del caso solicitado, red nominal, fichas de máquinas y clasificación de cargas; temperaturas de cables para MIN; revisión vinculada al modelo | [P4](P4_IEC60909.md), [máquinas](SC3_MACHINES.md), [Brno MAX](BRNO_SC3_MAX_REPLAY.md). Se puede pedir un solo caso sin inventar el otro |
| Cortocircuito 2F / 1F-T | pandapower | Datos admitidos por P4; para tierra, secuencia cero y neutros explícitos | [P4](P4_IEC60909.md). Z2=Z1 en el alcance pasivo simétrico; las fichas SC de máquinas no se trasladan por inferencia |
| Pico ip / equivalente térmico Ith | pandapower | Red admitida sin fichas SC de máquinas, topología, método kappa y duración explícitos | [P4](P4_IEC60909.md). No equivale al tiempo de despeje; con máquinas sigue excluido |
| Ampacidad y protección del conductor | Tablas y verificaciones MCP | Conductor, instalación, factores aplicables, evidencia normativa, Ib/In y criterio | [Matriz](MATRIZ_CAPACIDADES_ACTUALES.md). Solo filas/factores demostrados; no búsqueda normativa automática |
| Corte, despeje y coordinación temporal | Curvas y verificaciones MCP | Dispositivo/rating, corriente vinculada, curvas y bandas, unidades y semántica de tiempo; relación de corrientes y margen explícitos | [P5](P5_PROTECTION_TCC.md), [intervalo continuo](P5E_COORDINACION_INTERVALO.md). No selectividad integral ni curvas inventadas |
| Energía pasante y cable | Verificación MCP | I²t total publicado para el dispositivo/punto, capacidad de corte, k y sección | [Q12C](ENERGIA_PASANTE_Q12C.md). No deriva una TCC desde I²t |
| Compensación reactiva | OpenDSS | Demanda, etapas y criterios | [Banco estático](COMPENSACION_REACTIVA_OPENDSS.md). Sin calificación de resonancia/control automático |
| Armónicos y barrido | OpenDSS | Espectros y modelo de red/amortiguamiento explícitos | [Q6](ARMONICOS_OPENDSS.md). Alcance no triplén y secuencia positiva publicado |
| Daily / Yearly | OpenDSS | Perfiles P/Q, pasos, periodo y criterios | [Q7](SERIES_TEMPORALES_OPENDSS.md). Energía y balances del periodo declarado |
| Actuación de relés | pandapower OCRelay | Tipo y ajustes DTOC/IDMT/IDTOC, corrientes constantes y datos explícitos | [Q8](ACTUACION_RELES_PANDAPOWER.md). Tiempo de relé separado del interruptor |
| Arranque estático / perfiles / secuencias | OpenDSS | Corriente/fp y estados o puntos temporales declarados | [P13](P13_MOTOR_STARTING.md). No calcula aceleración mecánica |
| Arranque dinámico DOL / SCR | OpenModelica/MSL | Paquete de máquinas, red RL común, carga mecánica y controles admitidos | [DOL](MSL_DOL_VERIFICACION.md), [dos SCR](MSL_SCR_DOS_MOTORES.md). Bancos una/dos máquinas; SCR delta, sin VFD ni traducción automática de toda la planta |
| Falla terminal de motor EMT | OpenModelica/MSL | Un motor estrella, velocidad impuesta y paquete Q13A explícito | [Q13A](MOTOR_FAULT_THERMAL_EMT.md). Ondas e integral i²t por fase; no Ith IEC con máquinas |
| Expediente y reconstrucción | MCP | Modelo, datos y criterios del contrato solicitado | [P7](P7_ENGINEERING_PREVIEW.md), [aceptación P8](USO_PROFESIONAL_CONTROLADO.md). Hash/replay no certifican la física de entradas; P7B requiere revinculación según contrato |

2F-T conserva su condición de extensión de uso técnico interno y contraste
externo pendiente; no se agrupa con 3F/2F/1F-T calificados. IEEE 1584 continúa
diferido. Los límites específicos completos están en la
[matriz detallada](MATRIZ_CAPACIDADES_ACTUALES.md).

## Brno: evidencia disponible y datos pendientes

- Flujo: contraste en 269 barras, con semántica de carga todavía por confirmar.
- Cortocircuito: Ik'' 3F MAX publicado en 11 etiquetas de barra / 8 nodos,
  con 73 grupos equivalentes; error relativo máximo aproximado 7.45e-8.
- Sensibilidad: factor BT 6 → 10 → 6, revisión anterior rechazada al cambiar
  opción y recuperación del resultado original. La variante no tiene una
  referencia externa propia y no se presenta como mínimo real.
- Pendientes del proyecto: fuente/configuración/temperaturas MIN justificadas,
  revisión LF/SC común, tierra y curvas/ajustes con unidades autenticadas.
- No se afirma visita, medición de planta ni cierre integral de la instalación.

## Comprobar que la instalación local corresponde a esta capacidad

El código remoto, su CI y el proceso instalado en una PC son evidencias distintas.
El fallo actual del ejecutor de esta sesión impide leer o actualizar la PC:
`file:///workspace` es inválido en Windows al iniciar PowerShell. No hay
comprobación local nueva ni se afirma que el servidor de esa PC esté actualizado.

Desde la carpeta real del repositorio, una sesión local operativa puede ejecutar:

```powershell
git status --short
git fetch origin
git pull --ff-only
git rev-parse HEAD
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe scripts/verify_local_mcp.py
```

Revisar cambios locales antes de actualizar; no descartarlos ni forzar el pull.
La verificación stdio crea un proceso y modelo de referencia propios y conserva
`verification.json`/expedientes en la ruta de salida que informa el script.
No acredita que un cliente ya abierto haya recargado su proceso.

Después hay que reiniciar o reconectar el cliente MCP real y verificar su
catálogo y una operación desde ese cliente. La versión de referencia registra
174 herramientas, incluidas `ejecutar_estudio` y
`definir_grupo_motores_equivalente_3ph`; el número solo no prueba la revisión
instalada. Conservar SHA, intérprete/configuración del cliente, catálogo y
resultado de prueba sin credenciales. Para transporte HTTP, usar una sesión
de prueba dedicada: el verificador construye modelos de referencia y no debe
ejecutarse sobre un modelo de trabajo sin guardarlo antes.
Ver [instalación y transportes](P14_LOCAL_RUNTIME.md).

El cierre local queda pendiente hasta obtener esa evidencia de la PC y del
cliente; no se sustituye por un resultado de CI.
