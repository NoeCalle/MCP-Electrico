# Expediente para cerrar una instalación real: fábrica alimentaria Brno

**Estado: bloqueado para validación integral.** Se recuperó un proyecto ETAP
original de una instalación industrial existente y se auditaron sus exportaciones.
Se ejecutó y comparó una proyección de flujo de esta fábrica mediante P8/OpenDSS.
Cortocircuito y protección de la instalación aún no están reproducidos.
El auditor original sigue acreditando únicamente la lectura reproducible de la
fuente. El replay eléctrico y su evidencia se ejecutan por separado. Ninguno
cierra la validación integral ni acredita mediciones de campo.

## Fuente obtenida

Máté Áron Polák, *Electrical Power Network Model of an Industrial Facility in
ETAP*, Brno University of Technology, 2026. La página 31 describe una fábrica
alimentaria checa anonimizada, documentación del establecimiento y visita del
autor. La página 3 identifica a Schneider Electric CZ como colaborador industrial.
Esto respalda su procedencia; no es una inspección de campo realizada por nosotros.

- Ficha oficial: https://www.vut.cz/studenti/zav-prace/detail/176344
- Tesis, 102 páginas: https://www.vut.cz/www_base/zav_prace_soubor_verejne.php?file_id=299910
- Anexo original: https://www.vut.cz/www_base/zav_prace_soubor_verejne.php?file_id=299911
- Metadatos y hashes: [manifiesto](../examples/qualification/brno_industrial_2026.json).

El portal DSpace daba error 500. La copia pública del portal de la universidad
permitió obtener la tesis y su ZIP sin eludir controles de acceso. El ZIP contiene
el MDF/LDF del proyecto, respaldo, hojas de cálculo y tres bases SQLite de
informes. El auditor lee solamente estas últimas en modo inmutable/read-only.
No ejecuta scripts incluidos ni abre el proyecto en ETAP. La recuperación
adicional del MDF usa otro script y una copia temporal en SQL Server 2019,
según se detalla abajo. No se redistribuyen
la tesis, el ZIP ni los archivos originales.

## Qué se comprobó en los archivos

Todos los encabezados SQLite indican `BKLRSKPRCAMDLZ`, ETAP `24.0.3E` y
fecha `20-05-2026`. Estos metadatos no prueban identidad eléctrica del modelo.
Los recuentos siguientes son filas del informe, no equipos energizados verificados.

| Exportación | Barras | Cables | Transformadores | Conexiones |
|---|---:|---:|---:|---:|
| `Untitled.LF1S` — flujo | 273 | 244 | 12 | 270 |
| `Untitled.SI1S` — cortocircuito | 267 | 238 | 12 | 264 |
| `Untitled.SQ2S` — secuencia | 267 | 238 | 12 | 264 |

Hay seis cables adicionales en flujo: `LV.22-WL0.2`, `LV.32-WL0.1`,
`LV.42-WL0.1`, `N°1`, `N°217` y `N°59`. La omisión de ramas en ciertos
estudios podría ser una proyección válida; necesita documentarse, no demuestra
por sí sola un error del software ni una revisión incompatible.

| Campo observado | Flujo | SC | Secuencia | Tratamiento |
|---|---|---|---|---|
| `IXFMR2.PhaseAngle`, los 12 transformadores | 0° | 0° | 30° | Reconciliar con Dyn1 documentado y la semántica de exportación; no cambiar para ajustar resultados. |
| `Icable.TempOp`, todos los cables | 75 °C | 20 °C | 75 °C | Son opciones de estudio potencialmente válidas; conservar escenarios y justificar proyección MAX/MIN. |
| `IXFMR2.SecGrdType`, los 12 transformadores | Petersen Coil | Petersen Coil | Petersen Coil | Aclarar ubicación: la memoria declara BT TN-C y compensación en MT; no convertir la BT automáticamente en neutro sólido. |

La geometría de cables SC/secuencia coincide en ID, extremos, sección, longitud
y paralelos. Esto no verifica estados de interruptores, todas las impedancias,
curvas, fuentes ni identidad completa de las dos ejecuciones.

El PDF de informe `Untitled.LF1S - Complete.pdf` incluido en el mismo ZIP
declara fecha `02-04-2026`, 227 barras, 210 cables y 228 ramas en su página 1.
No se usan sus resultados como referencia del SQLite de mayo, con 273 barras.

## Protecciones: evidencia disponible y límite

`SeqOfOperFaultSpec` conserva una sola ubicación, `Bus194`. `SeqOfOper`
tiene 11 filas: dos con actuación y nueve con `DID NOT TRIP` y valor centinela
`-1000`. Este centinela no es un tiempo negativo físico, y la ausencia de
disparo de una protección ajena a la falla no demuestra una falla de protección.
Los valores de tiempo quedan crudos: no se ha autenticado su unidad ni se
convierten en tiempos de despeje total de interruptor.

Una secuencia guardada no sustituye una tabla de ajustes y curvas de los
272 interruptores BT y seis MT que describe la memoria (páginas 34-35), ni
demuestra selectividad en todos los puntos MAX/MIN. Las tablas AutoStar
consultadas están vacías; no se afirma que el MDF original carezca de ajustes.
La recuperación adicional del MDF sí obtuvo identidades, ratings y ajustes
crudos de muchos dispositivos. Todavía falta autenticar unidades, biblioteca,
curvas y correspondencia de revisión; una fila con un modelo no equivale a
una banda TCC completa de despeje total.

## Lo que debe resolverse antes del cierre

1. **Revisión común:** congelar el proyecto y exportar entradas/resultados de
   flujo, SC MAX/MIN y protecciones, con estados de maniobra y proyecciones
   por estudio. Resolver ángulos y correspondencia abril/mayo.
2. **Puesta a tierra:** reconciliar la memoria de MT compensada/BT TN-C con
   las bobinas registradas en secundarios BT. No inferir el modelo homopolar.
3. **Equipos y ajustes:** exportar identidad, unidad de disparo, curvas,
   tolerancias, ajustes y capacidad de corte a su tensión, con semántica de
   tiempo de relé, apertura y despeje total. Cubrir los puntos de falla requeridos.
4. **Supuestos de la fuente:** el autor declara longitudes y datos operativos
   estimados (página 31), sustituciones térmico-magnéticas/electrónicas
   (34-35) y factores de carga estimados (35-36). La página 60 pide datos
   reales y validación contra la instalación. Pueden servir para reproducir
   el modelo académico, si se declaran; no pasan a ser mediciones de campo.
5. **Alcance del MCP:** SC3 admite su contrato de corriente inicial, no el
   decaimiento/Ith con máquinas utilizado por esta memoria. El modelo de
   neutro compensado tampoco se debe aproximar silenciosamente al P4
   admitido. Se requiere ampliar y calificar esos contratos, o definir otro
   alcance real documentado que ya esté soportado. Disponer del ZIP no
   elimina estas limitaciones del software.

El [paquete de datos solicitado](PAQUETE_PARA_CERRAR_INSTALACION_REAL.md)
concreta qué exportar y cómo se comprobará. Usa los gates P8/P2/P3/P4/P5
existentes; esta auditoría no crea otra vía de aprobación ni una herramienta MCP.

## Repetición de la auditoría

```powershell
python scripts/audit_brno_industrial_archive.py --verify-upstream --output outputs/brno-audit/source-audit.json
```

Sin conexión, con el ZIP previamente verificado:

```powershell
python scripts/audit_brno_industrial_archive.py --archive outputs/brno-source/299911.zip --output outputs/brno-audit/source-audit.json
```

Comprueba SHA256 de tesis/ZIP y tres SQLite, recuentos, diferencias declaradas,
ángulos, temperaturas y cobertura de la secuencia. Si la universidad cambia
un byte, falla y pide revisar la nueva fuente. `audit_reproduced=true` convive
con `installation_validation_closed=false`. La evidencia de CI se registra
por separado; no se altera la calificación Q11 ni el número de herramientas.


## Recuperación adicional y primer cálculo eléctrico reproducido

La lectura del MDF original se consiguió con LocalDB 2019 (formato interno
SQL Server 904). El lector 2025 intentaba actualizar una base marcada
read-only y rechazaba la apertura; no se modificó el archivo original para
superar ese rechazo. Se descargó el runtime 2019 desde Microsoft, se verificó
su firma y se usó solamente en el runner temporal. La instalación automatizada
acepta los términos de LocalDB **en ese runner**, no instala nada en el equipo
del usuario. La fuente está fijada por SHA256 y nunca se ejecuta ETAP,
procedimientos, vistas, ensamblados ni scripts incluidos en el ZIP.

Se enumeraron 504 tablas físicas no vacías; muchas contienen registros
predeterminados y esos recuentos **no equivalen a equipos instalados**.
Entre las filas con `IID > 255` se recuperaron:

- 12 transformadores: los 12 conservan el tipo crudo de secundario `6`
  y el parámetro reactivo paralelo de la bobina. No queda resuelta la
  contradicción BT TN-C/compensación; tampoco se convierte a neutro sólido.
- 74 filas de cargas agrupadas, todas `Conventional` y
  `ConstantZPercent=20`. Se conserva la diferencia con las 73 filas
  participantes en el informe.
- 280 filas de interruptores BT: 275 tienen modelo y fabricante;
  274 tienen tensión, corriente y capacidad de corte IEC positivas.
  Cinco no tienen modelo: `CB61.3`, `CB61.4`, `CB61.5_1`,
  `CB61.5_2` y `CB178`. La participación/ausencia debe reconciliarse
  con las configuraciones, no completarse por analogía.
- Ajustes crudos térmico-magnéticos y electrónicos, incluyendo pickups,
  retardos, etiquetas y campos de unidad. No se interpretan multiplicadores
  sin autenticar la semántica del fabricante.

### Flujo de mayo: alcance del replay

`scripts/replay_brno_loadflow_research.py` construye un manifiesto P8
desde **entradas del mismo LF1S**, no desde sus tensiones, corrientes ni
potencias calculadas. Usa `IBus`, `Icable`, `IXFMR2`, `IConnect` e
`ILFStudyCase`. Los resultados `LFR` y `LFSumTotal` se leen solo para
comparar. No se mezcla el PDF de abril.

La proyección declara cargas motor como PQ constante, cargas estáticas como
Z constante, C1 a partir de la admitancia y frecuencia, paralelos de cable y
tap nominal fijo explícito. Los 14 enlaces exportados con impedancia cero
incluyen 11 interruptores, un seccionador y dos busducts; se fusionan sus
barras con un mapa trazable. Cuatro barras sin carga quedan fuera del
componente alimentado desde HV1: `Bus43`, `Bus49`, `N°59~` y `N°1~`.
Los dos generadores quedan fuera de este alcance normal y no se califican
sus estados de emergencia.

La fuente es el contrato PF `QUASI_IDEAL_SLACK`: 100 MVA, R=X=1e-6 pu,
tolerancia 1e-9 e iteraciones máximas 99. No representa impedancia de
cortocircuito. Se conserva D/Y y se proyecta Dyn1 según la memoria; se
comparan magnitudes y pérdidas, **no los ángulos HV/BT**. La semántica
completa de la proyección del programa de origen continúa bajo revisión:
el estado del resultado es
`RESEARCH_ONLY_LOAD_MODEL_SEMANTICS_UNCONFIRMED`.

El replay pasó por `real_controlled_execution.ejecutar_controlado`, sin
saltar sus gates P8. En la ejecución documentada:

| Comparación | Resultado |
|---|---:|
| Barras originales | 273 |
| Barras conectadas comparadas | 269 |
| Mayor error de magnitud | 2.165e-7 pu, aproximadamente |
| Pérdidas activas OpenDSS | 255.0784 kW |
| Pérdidas activas LF1S | 255.0784 kW |
| Pérdidas reactivas OpenDSS | 623.7273 kvar |
| Pérdidas reactivas LF1S | 623.7099 kvar |

Criterios del replay: 1e-4 pu de error absoluto de magnitud y 0.1% de
error relativo en P/Q agregadas de fuente y pérdidas. Se exige convergencia,
269 comparaciones y valores finitos; salir de tolerancia falla el workflow.
Un resultado próximo por sí solo no autentica cada opción de ETAP ni
califica el resto de estudios.

Se corrigió un bloqueo del contrato P2: ahora puede declararse un **tap
nominal fijo** con min=max=neutral=posición=0 y paso=0. Antes el gate exigía
un paso positivo incluso sin regulación. Omitir los taps sigue bloqueando
el caso real; paso cero con rango ajustable o posición diferente sigue
rechazado. No se inventa un paso para conseguir la admisión.

`scripts/verify_brno_loadflow_mcp.py` comprueba por MCP stdio la admisión, construcción sin Solve, readiness PF,
flujo, snapshot P7A, hash, reporte P7C y reconstrucción P7B. El generador
integral P8E2 exige P5: su rechazo de un manifiesto PF-only también se prueba
y se conserva. El reporte PF no se presenta como dossier integral P3/P4/P5.

### Repetición

```powershell
python -m pytest tests/test_transformer_fixed_nominal.py -q
python scripts/replay_brno_loadflow_research.py
python scripts/verify_brno_loadflow_mcp.py
```

Las salidas incluyen manifiesto derivado, ejecución P8, comparación por
barra, llamadas MCP, snapshot verificable, reporte y reconstrucción. La recuperación MDF y
los resultados eléctricos se guardan en artefactos distintos del workflow
`brno-source-recovery`. El ZIP/MDF/LDF originales y el runtime de Microsoft
no se incluyen en esos artefactos.

**Pendiente para cerrar la instalación completa:** una revisión común y sus
escenarios MAX/MIN, resolver el modelo de neutro, autenticar las curvas y
unidades/capacidades de todos los dispositivos participantes y completar la
comparación de SC/protecciones. Ith con máquinas y neutro compensado
continúan fuera de los contratos calificados. La validación de campo requiere
evidencia de campo; la recuperación de archivos no la sustituye.
