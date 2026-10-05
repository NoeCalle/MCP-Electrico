# Contraste SCR con el ejemplo original de MSL

## Método

`scripts/verify_msl_scr_native_mcp.py` ejecuta dos rutas separadas:

- Referencia: hereda `Modelica.Electrical.PowerConverters.Examples.ACAC.SoftStarter`, con su máquina `Magnetic.FundamentalWave.IM_SquirrelCage` y conexiones originales de convertidor/control.
- MCP: llama `ejecutar_dinamica_modelica` mediante un servidor stdio nuevo. El adaptador configura la máquina `Electrical.Machines.IM_SquirrelCage` de MSL.

Ambas rutas usan OpenModelica 1.27.1/MSL 4.0.0. Esta es una comprobación de integración y equivalencia entre dos formulaciones de máquina de la biblioteca; no un contraste con otro simulador ni una calibración de fabricante.

La referencia declara las adaptaciones: fuente ideal de 100 V entre líneas, carga mecánica nula, filtro de primer orden y componentes nativos de snubber RC y bypass. No modifica las fuentes de la biblioteca. No sirve como motor de producción.

Los límites se escriben antes de ejecutar: error de corriente, par y velocidad ≤0,1 % de sus escalas declaradas; tensión y consigna ≤0,001 pu; aceleración y bypass ≤0,001 s. Son tolerancias de comparación numérica, no mínimos normativos ni aceptación de un diseño industrial.

## Diferencias detectadas y resueltas en la preparación de la referencia

El primer ensayo, con paso nominal de 25 µs y refinado de 12,5 µs, incumplió el refinamiento de tensión: 0,002030 pu. Se conservó el límite de 0,001 pu y se redujeron los pasos a 12,5 y 6,25 µs. El refinamiento pasó con 0,000535 pu.

El contraste del par todavía difería 0,137239 %. La lectura independiente del CSV y la lectura del MCP sobre la misma traza coincidieron hasta errores menores a 1e-12 relativos. Se revisaron entonces los parámetros realmente inicializados por el simulador.

El filtro original `CriticalDamping`, de orden 1 y `normalized=true`, normaliza a **−3,0 dB**, usando `sqrt(10^(3/10)-1)`. Con `f_cut=1/(2*pi*0.02)` su polo era −50,11886465 s⁻¹, frente a −50 s⁻¹ en el `FirstOrder(T=0.02)` del MCP. La especialización correcta de la referencia usa `normalized=false`: conserva el componente MSL y obtiene el polo exacto −50 s⁻¹. La herramienta comprueba ese polo antes del ensayo completo.

Se corrigió la referencia de prueba; no se cambió la física de producción ni se relajaron las tolerancias.

## Primer caso corregido

| Métrica | Error observado | Límite prefijado |
|---|---:|---:|
| Corriente por ciclo | 0,0000459 % | 0,1 % |
| Par medio por ciclo | 0,0004021 % | 0,1 % |
| Velocidad | 0,0000141 % | 0,1 % |
| Tensión entre líneas | 0,00017475 pu | 0,001 pu |
| Consigna de tensión | 0,0000000365 pu | 0,001 pu |
| Tiempo hasta 90 % de velocidad síncrona | 0,0000000944 s | 0,001 s |
| Cierre del bypass | 0,0000000609 s | 0,001 s |

El caso se repitió desde cero y volvió a pasar. El banco ampliado incluye fase de fuente 0°, +15° y −27°; 50/60 Hz; inercia externa 0,29/0,58 kg·m²; y tensión inicial 0,3/0,4 pu. Su resultado global se declara únicamente cuando todas las ejecuciones terminan y pasan.

## Comprobaciones adicionales

`scripts/check_msl_scr_trace.py` comprueba, sin usar los resúmenes del adaptador:

- En estos casos sin carga ni amortiguamiento, `integral(par * velocidad * dt)` frente a `0.5 * (J_motor + J_carga) * delta(velocidad²)`. Límite relativo prefijado: 0,0001. La inercia del estator fijo no se suma.
- Tiempo de bypass frente al intervalo continuo durante el que consigna y velocidad cumplen sus umbrales, con reinicio de la espera si dejan de cumplirlos. Límite: dos pasos de salida más 1e-8 s.
- Permanencia del enclavamiento, trazas completas, tiempo ordenado y datos finitos.

La cuadratura conserva ambos lados de las conmutaciones. Los saltos de duración nula no se convierten en rampas ficticias para el cálculo RMS.

Las pruebas ordinarias de CI verifican los lectores y los contratos. El banco físico necesita el runtime fijado y conserva aparte Modelica generado, comandos, logs, CSV, entradas, métricas, tolerancias y hashes.

## Reproducción

Tras configurar el runtime local del MCP:

```powershell
.venv/Scripts/python.exe -X utf8 scripts/verify_msl_scr_native_mcp.py --output ruta-nueva
.venv/Scripts/python.exe -X utf8 scripts/check_msl_scr_trace.py --evidence ruta-nueva
```

`--first-only` ejecuta el caso base; `--cases phase-positive inertia` selecciona casos concretos. Cada salida usa un directorio nuevo. Un caso fallido conserva sus comparaciones y llamadas MCP, y no genera una evidencia global aprobada.

El alcance sigue siendo controlador genérico MSL y una máquina delta con parámetros explícitos. Las variantes de fabricante, estrella, multimotor SCR y traducción automática de todo el unifilar requieren pruebas distintas. La revisión y aprobación del estudio corresponden al ingeniero.

## Resultado del banco completo — Q4

Seis casos aprobados, 21 respuestas MCP stdio conservadas y nueve intentos físicos (incluye dos refinamientos de tensión no aprobados y un timeout sin resultado verificado). Hubo 22 peticiones: una agotó la espera del cliente y no devolvió una respuesta; su fallo del servidor se conservó aparte. Las doce trazas finales para balance de energía y política de bypass aprobaron. Se consolidaron ejecuciones existentes después de re-leer independientemente todos los CSV y comprobar los modelos generados contra los constructores vigentes.

Los casos de mayor inercia y menor tensión inicial necesitaron pasos nominal/refinado de 6,25/3,125 µs para pasar el mismo límite de tensión. Los otros cuatro usaron 12,5/6,25 µs. Un intento de tres segundos con la menor tensión inicial agotó el presupuesto de ejecución: aunque había CSV, se rechazó como resultado no verificado. Su repetición completa de 2,1 s terminó correctamente y cubrió aceleración, cierre del bypass y funcionamiento posterior; la espera del cliente se amplió para cubrir las etapas del servidor. No se reutilizó el intento fallido como resultado aprobado.

| Caso | Error corriente (%) | Error par (%) | Error tensión (pu) | Aceleración desde orden (s) | Bypass desde inicio de simulación (s) |
|---|---:|---:|---:|---:|---:|
| base | 0.0000459 | 0.0004021 | 0.0001748 | 1.2388687 | 1.8863928 |
| phase-negative | 0.0000338 | 0.0002839 | 0.0003865 | 1.2411191 | 1.8891823 |
| phase-positive | 0.0000502 | 0.0003963 | 0.0003346 | 1.2394433 | 1.8866721 |
| frequency-60 | 0.0000642 | 0.0002540 | 0.0005609 | 1.7337520 | 2.2841775 |
| inertia | 0.0000265 | 0.0002295 | 0.0000533 | 1.7795934 | 2.3608366 |
| initial-voltage | 0.0002036 | 0.0012905 | 0.0001025 | 1.3435442 | 1.9050724 |

La evidencia compacta, hashes y parámetros están en `mcp_electrico/data/msl_scr_native_evidence_v1.json`. Los CSV y logs originales se conservan en el expediente local. Las tres regresiones RL publicadas en Q3 y la referencia resistiva complementan este contraste con fuente ideal. No se modificó la física del adaptador al cerrar estos gates.

Los hashes de bytes conservan la procedencia de las ejecuciones. CI comprueba además hashes del mismo texto con finales de línea LF, para admitir los checkouts CRLF de Windows y LF de Linux sin ocultar cambios de código.
