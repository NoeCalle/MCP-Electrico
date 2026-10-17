# Expediente para cerrar una instalación real: fábrica alimentaria Brno

**Estado: bloqueado para validación integral.** Se recuperó un proyecto ETAP
original de una instalación industrial existente y se auditaron sus exportaciones.
No se ejecutó flujo, cortocircuito ni protección de esta fábrica mediante el MCP.
Un CI verde de esta auditoría acredita la lectura reproducible de la fuente;
no acredita resultados eléctricos ni cierra la instalación.

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
No ejecuta scripts incluidos ni abre el proyecto en ETAP. No se redistribuyen
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
Hace falta exportarlos mediante ETAP y conservar biblioteca/modelo y versión.

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
