# Armónicos y barrido de impedancia — Q6

Fecha: 16 de octubre de 2026. Integración nativa OpenDSSDirect 0.9.4 /
DSS-Python 0.15.7 / backend 0.14.5. El adaptador no contiene un solver físico.

## Alcance verificado

- Red trifásica equilibrada pasiva a 50/60 Hz, fuente Thevenin, líneas, transformadores
  de dos devanados, cargas y bancos ideales explícitos.
- Espectros de corriente de carga: órdenes enteros 2..50, excluidos múltiplos
  de tres. Se declara cada carga, incluso las lineales con espectro vacío.
- Magnitud de cada orden en porcentaje de la corriente fundamental resuelta
  de la carga, y ángulo en grados según la convención Spectrum de OpenDSS.
  No se deduce un espectro desde la etiqueta VFD/SCR ni desde potencia nominal.
- Tensión fase-neutro por barra y corriente de terminal de líneas,
  transformadores y capacitores. THDv por fase referida a la tensión
  fundamental resuelta, **truncada a los órdenes declarados**.
- Barrido de impedancia en secuencia positiva, con un Isource nativo de
  1 A por fase en una barra por ejecución y sin inyecciones armónicas de cargas.
  Las admitancias pasivas de carga y bancos se conservan. Z = Vfase / Iinyectada.
  Los órdenes del barrido pueden ser fraccionarios; esto no habilita emisiones
  interarmónicas ni convierte un barrido positivo en un estudio de secuencia cero.

## Aproximaciones que el paquete debe aceptar

`frequency_model=CONSTANT_R_LINEAR_X_NO_SKIN_EFFECT`: resistencia constante,
reactancia proporcional a frecuencia y capacitancias ideales. Se fuerza
`Line.Rg=Xg=0`, `Transformer.XRConst=No`, `ppm_Antifloat=0` y BaseFreq explícita.
No hay efecto pelicular, pérdidas de filtros ni dependencia de frecuencia de
datos de fabricante. El constructor compartido fija DefaultBaseFrequency
**antes** de crear el circuito: Frequency en Circuit solo no bastaba a 50 Hz.

`neglect_load_y=false`: se conserva el amortiguamiento declarado mediante
`series_rl_percent` por carga. El resto corresponde al equivalente paralelo
R/L nativo. `puXHarm=0` utiliza P/Q nominales; XRHarm no interviene en ese caso.
Las demandas capacitivas se representan como bancos, no como cargas RL negativas.
La fuente de tensión es sinusoidal, con espectro solo fundamental.

La verificación de KCL usa la matriz dispersa nativa y sus vectores `YV-I`.
No suma Load.GetCurrents: en este backend esos medidores no representan
necesariamente toda la admitancia Norton en modo armónico. No se publican esas
corrientes de carga como corriente total de terminal. El adaptador solo
multiplica la matriz para verificar el residuo; OpenDSS resuelve el circuito.

## Criterios y máximos del barrido

El usuario declara el límite de THDv y su referencia. `criteria.passed=false`
puede ser un resultado válido de cálculo. No convergencia, fasores inválidos,
frecuencia incorrecta o exceso de residuo bloquean resultados evaluables.

`sampled_local_peaks` identifica máximos locales entre muestras vecinas; no
certifica la frecuencia exacta ni detecta todos los modos de resonancia.
Se requiere refinar el intervalo, rango y amortiguamiento para un estudio de
ingeniería. Un extremo del barrido no se clasifica como pico interior.
No se verifica IEEE 519, TDD, PCC ni aceptación automática de dispositivos.

## Uso y trazabilidad

1. `obtener_contrato_armonicos` presenta alcance y exclusiones.
2. `validar_armonicos(paquete_estudio)` valida sin cálculos ni archivos.
3. `ejecutar_armonicos(paquete_estudio, directorio_salida)` crea contextos
   aislados, ejecuta y guarda Inputs.json, Results.json, Informe.html e Integrity.json.

Ejemplo completo: [harmonics_stage1.json](../examples/harmonics_stage1.json).
El selector genérico informa la ruta pero no habilita una ejecución sin validar
el paquete. Un directorio existente se rechaza; no se sobrescriben estudios.
Un fallo numérico conserva su expediente como inválido. El circuito/workspace
padre no se modifica. El informe HTML incluye tablas e impresión del navegador;
la integración en una pestaña del workspace permanece como mejora visual.

## Evidencia reproducible

```powershell
python -m pytest tests/test_harmonics.py tests/test_reactive_compensation.py -q
python scripts/verify_harmonics_mcp.py --output harmonics_evidence
```

El banco RL/C independiente cubre **24 combinaciones**: 50/60 Hz, wye/delta,
banco ON/OFF y fracción serie 0/50/100 %. Compara tensiones armónicas,
corrientes de línea, THDv y R/X/|Z| del barrido contra expresiones complejas
independientes del adaptador. Se contrasta también con un script DSS nativo.
Las tolerancias se fijan en las pruebas: 2e-6 V, 2e-5 A y 2e-7 ohm.

El ejemplo con transformador Dyn11 se contrasta contra
[un archivo DSS independiente](../examples/harmonics_transformer_native.dss).
Se prueban secuencias 5/7, cancelación de dos emisiones, espectros limpios,
rechazos de entradas, integridad de archivos, fallos del motor y aislamiento.
El [registro Q6](evidence/harmonics_q6_mcp.json) conserva métricas y hashes.
La verificación stdio realizó **54 llamadas MCP**, con 24 contrastes y el ejemplo
con transformador. Guarda métricas de error y hashes de fuentes en Evidence.json.

Los casos son sintéticos de integración. Se excluyen triplén/secuencia cero,
desbalance, fondo de tensión distorsionado, filtros desintonizados, efectos de
conmutación y conformidad normativa automática. Cada proyecto requiere sus
espectros, datos, criterios y revisión por el ingeniero.

## Fuentes primarias

- [EPRI — Harmonic Flow Analysis](https://opendss.epri.com/HarmonicFlowAnalysis.html).
- [EPRI — Harmonics Load Modeling](https://opendss.epri.com/HarmonicsLoadModeling.html).
- [DSS-Extensions — Load / SeriesRL y puXHarm](https://dss-extensions.org/dss-format/Load.html).
- [DSS-Extensions — Isource / ScanType](https://dss-extensions.org/dss-format/Isource.html).
- [DSS-Extensions — Transformer / XRConst](https://dss-extensions.org/dss-format/Transformer.html).
