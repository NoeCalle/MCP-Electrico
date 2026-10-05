# Dos motores con arrancadores SCR — integración MSL

## Circuito y alcance

Cada máquina delta tiene su propio controlador `SoftStartControl`, sensor, filtro, triacs, snubber y bypass MSL. Ambas ramas están conectadas a una única impedancia trifásica RL de alimentación. El MCP configura componentes, ejecuta OpenModelica y procesa resultados; no añade ecuaciones de máquina o arrancador en Python.

El generador ya construía ramas independientes. La ampliación modifica el contrato y la admisión para permitir dos máquinas SCR. No cambia `build_model`, `_summaries`, la ejecución ni el perfil DASSL/Newton. Se conservan hashes de esas secciones para no perder la vinculación del contraste original Q4 al ampliar la admisión.

Se mantienen bloqueadas más de dos máquinas cuando alguna usa SCR, combinaciones DOL–SCR y conexiones SCR en estrella. El disparo se refiere a la fuente sinusoidal aguas arriba. No se representa automáticamente un arrancador real de fabricante ni se traduce el unifilar OpenDSS completo.

## Banco de comprobación

Los casos son sintéticos con resistencias fijas y parámetros explícitos del ejemplo MSL. Seis usan carga mecánica cero; uno añade curvas de carga, amortiguamientos e inercias diferentes para cada rama. No son los motores de las bombas del proyecto.

| Caso | Frecuencia | Orden M1 / M2 | Comprobación principal |
|---|---:|---|---|
| Ideal simultáneo | 50 Hz | 0,1 / 0,1 s | Cada rama contra el ejemplo original MSL FundamentalWave |
| Control de una máquina con doble impedancia | 50 Hz | 0,1 s | Referencia para equivalencia simétrica de dos ramas |
| RL simultáneo | 50 Hz | 0,1 / 0,1 s | Dos ramas iguales con Z frente a una con 2Z |
| RL solapado | 50 Hz | 0,1 / 0,5 s | M2 comienza mientras M1 acelera; bypass independientes |
| RL después de bypass | 50 Hz | 0,1 / 2,0 s | M1 queda en marcha al arrancar M2 |
| RL solapado | 60 Hz | 0,1 / 0,5 s | Frecuencia y fase +15°; ventanas RMS no alineadas con el CSV |
| RL solapado con cargas distintas | 50 Hz | 0,1 / 0,5 s | Curvas de par, inercias y amortiguamientos diferentes por rama |

La equivalencia de impedancias no afirma equivalencia con cualquier motor: para dos ramas idénticas, simultáneas y simétricas, la corriente común es dos veces la de una rama. Por ello Z con dos ramas debe producir las mismas condiciones por máquina que 2Z con una. Las trazas se comparan cuantitativamente.

Además se comprueba, usando las corrientes instantáneas de **todas** las ramas:

`Vab_fuente - Vab_barra = R * suma(Ia - Ib) + L * d(suma(Ia - Ib))/dt`

La comprobación integra por ciclos con ponderación compleja e integración por partes, conservando el término de borde de la inductancia durante el transitorio. No diferencia numéricamente las corrientes de conmutación ni se limita a comparar RMS. Las dos salidas de tensión de barra deben coincidir.

Cada máquina debe conservar su balance de energía mecánica y su política de espera/enclavamiento del bypass. En el caso cargado se resta el trabajo de su propia curva de carga y de su propio amortiguamiento: `integral((par_electrico - par_carga - d*velocidad)*velocidad*dt) = delta(energia_cinetica)`. La curva se evalúa por interpolación de los puntos declarados, sin extrapolación. Se usan las trazas nominal y refinada completas; ninguna traza parcial se acepta como resultado.

## Límites prefijados

- Comparaciones por máquina: corriente/par/velocidad ≤0,1 % de las escalas declaradas; tensión/consigna ≤0,001 pu; diferencias de tiempos ≤0,001 s.
- Balance mecánico: error relativo ≤0,0001.
- Residuo de KVL: ≤0,001 pu; diferencia entre salidas de la misma barra ≤1e-8 V.
- Política de bypass: diferencia temporal ≤dos pasos de salida +1e-8 s, espera continua y enclavamiento permanente.
- Cada ejecución MCP requiere su refinamiento numérico de corriente, velocidad, tensión de barra/terminal, par y tiempos.

Son tolerancias de verificación numérica. Los mínimos de diseño y la aprobación del estudio los declara el ingeniero para su proyecto.

## Reproducción

```powershell
.venv/Scripts/python.exe -X utf8 scripts/verify_msl_scr_two_mcp.py --output directorio-nuevo-50hz
.venv/Scripts/python.exe -X utf8 scripts/verify_msl_scr_two_60_mcp.py --output directorio-nuevo-60hz
.venv/Scripts/python.exe -X utf8 scripts/verify_msl_scr_two_loaded_mcp.py --output directorio-nuevo-cargado
```

El primer comando ejecuta cinco casos, incluida una referencia de una máquina. `--cases` permite seleccionar casos; `--step` fija el paso antes de ejecutar. El segundo ejecuta el caso a 60 Hz y el tercero el caso con cargas distintas. Cada comando guarda entradas, modelos, trazas, llamadas MCP, refinamiento, límites, errores y hashes en directorios nuevos. La biblioteca y el compilador permanecen fijados por hashes.

La CI comprueba contratos, bloqueos y lectores independientes. El banco físico requiere el runtime OpenModelica/MSL instalado y conserva evidencia separada.

## Límites del resultado

El respaldo del modelo abierto y el refinamiento de un caso no califican automáticamente todos los parámetros, tipos de carga, dispositivos ni combinaciones. La ampliación verificada se publica únicamente cuando el banco termina y aprueba. La revisión y aprobación del estudio quedan a cargo del ingeniero.

## Resultado Q5

Los siete casos MCP aprobaron: seis de dos motores y un control de una máquina. Se conservaron dieciocho llamadas MCP, catorce trazas nominal/refinada y veintiséis comprobaciones por máquina de energía y bypass. El contraste ideal original y la equivalencia de impedancias aprobaron los mismos límites prefijados.

| Caso | Motor | Aceleración desde orden (s) | Bypass desde inicio (s) | Tensión mínima de barra (pu) |
|---|---|---:|---:|---:|
| ideal-simultaneous | SCR-1 | 1.238869 | 1.886393 | 1.000000 |
| ideal-simultaneous | SCR-2 | 1.238869 | 1.886393 | 1.000000 |
| single-double-Z | SCR-1 | 1.248951 | 1.870725 | 0.974008 |
| RL-simultaneous | SCR-1 | 1.248951 | 1.870725 | 0.974008 |
| RL-simultaneous | SCR-2 | 1.248951 | 1.870725 | 0.974008 |
| RL-overlapping | SCR-1 | 1.260547 | 1.880525 | 0.974610 |
| RL-overlapping | SCR-2 | 1.230573 | 2.215872 | 0.974610 |
| RL-after-bypass | SCR-1 | 1.244587 | 1.879940 | 0.985491 |
| RL-after-bypass | SCR-2 | 1.247945 | 3.782430 | 0.985491 |
| 60HZ-overlapping | SCR-1 | 1.766584 | 2.285670 | 0.974721 |
| 60HZ-overlapping | SCR-2 | 1.748659 | 2.689341 | 0.974721 |
| UNEQUAL-LOADED | SCR-1 | 1.313610 | 1.923284 | 0.974993 |
| UNEQUAL-LOADED | SCR-2 | 1.028600 | 2.034949 | 0.974993 |

El intento de 60 Hz a 3 s agotó el presupuesto de ejecución refinada y quedó sin resultado verificado. Su nueva ejecución a 2,8 s conservó ambos arranques, ambos bypass y el funcionamiento posterior; aprobó sin relajar tolerancias. Una ejecución inicial se detuvo intencionalmente para corregir la cuadratura del lector en ventanas no alineadas con el CSV; no se cambió el circuito físico.

La evidencia compacta está en `mcp_electrico/data/msl_two_scr_evidence_v1.json`. Las llamadas conservan el estado del registro de su fecha: la ampliación estaba en verificación durante el banco y se cerró después de aprobarlo. No se reescriben snapshots históricos.
