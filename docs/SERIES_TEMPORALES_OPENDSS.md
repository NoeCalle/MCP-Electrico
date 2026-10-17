# Perfiles Daily/Yearly — Q7

Fecha: 16 de octubre de 2026. Motor nativo OpenDSSDirect 0.9.4 /
DSS-Python 0.15.7 / backend 0.14.5. El MCP prepara datos, ejecuta y procesa
medidores; no incorpora un segundo solver eléctrico.

## Alcance

Red trifásica equilibrada a 50/60 Hz, fuente Thevenin fija, líneas,
transformadores de dos devanados y cargas constantes PQ o impedancia. Cada
carga recibe arrays **independientes y completos de P y Q** como multiplicadores
de sus valores nominales. La demanda real de una carga de impedancia varía
también con su tensión: el informe no confunde multiplicador con kW medidos.

Las cargas se traducen a LoadShape nativos con Interval regular, Mult y Qmult
explícitos, UseActual=No y sin normalización. El perfil puede incluir carga
cero o factores mayores que uno. No se imputan datos faltantes ni se copia P
automáticamente a Q. Las identidades y referencias conservan el vínculo con
cada carga de la red base.

## Tiempo y energía

- Horas transcurridas desde cero; no son fechas civiles ni zonas horarias.
- Daily exige un perfil completo de 24 h, con un paso que divida exactamente
  ese periodo. Una ejecución más larga exige `repeat_daily_profile=true`.
- Yearly utiliza un punto por cada paso solicitado. No repite un perfil corto
  ni inventa las horas restantes de un año. Un estudio de tres horas en modo
  Yearly sigue siendo un estudio de tres horas.
- Horizonte máximo de 8.784 h y 35.136 pasos; los tamaños de red/resultado
  también están acotados. Un estudio horario de 8.760 h está probado.
- Cada Solve nativo avanza exactamente un intervalo. La lectura posterior de
  medidores no ejecuta otro Solve ni avanza el reloj por segunda vez.
- Los valores se evalúan al final de cada intervalo: el punto 0 del perfil
  corresponde al intervalo (0, Δt], no a una muestra adicional en t=0.
- La energía es la suma rectangular de potencia final por Δt explícito.
  Representa la aproximación por intervalos declarada; no es integración EMT
  ni una predicción anual automática.

El consumo de fuente se mide en el terminal externo de Vsource. El balance
activo incluye cargas y pérdidas de líneas/transformadores; excluye las
pérdidas internas del equivalente Thevenin. Las pérdidas del transformador
están incluidas cuando ese equipo forma parte de la red declarada.

## Resultados y validez

Por intervalo: tensiones por fase/barra, kW/kvar de fuente, demandas reales por
carga, corrientes y cargabilidad de líneas, potencia/cargabilidad de
transformadores, pérdidas y residuo de balance. Se conserva el índice de
perfil aplicado y ambos multiplicadores.

El resumen contiene energía de fuente y cargas, energía de pérdidas, demanda
máxima y su hora final, tensión mínima y máximas cargabilidades. Los criterios
de tensión y carga de equipos son explícitos y referenciados por el proyecto.
Un resultado que excede un criterio puede ser numéricamente válido. La salida
de los límites Vminpu/Vmaxpu de una carga PQ se identifica como incumplimiento
de su representación, siguiendo el medidor compartido existente.

No convergencia, fallo del motor o desequilibrio de potencia interrumpen la
serie. Se conservan los pasos anteriores y el paso inválido; **no se publica
energía ni demanda máxima del horizonte completo desde una serie parcial**.
No se reutilizan valores anteriores como si fueran el paso fallido.

## Herramientas y archivos

1. `obtener_contrato_series_temporales` muestra límites y semántica.
2. `validar_series_temporales` comprueba entradas sin resolver ni escribir.
3. `ejecutar_series_temporales` crea un contexto aislado y devuelve resultados.

[Ejemplo con dos cargas y transformador](../examples/time_series_stage1.json).
Se guardan Inputs.json, Results.json, Series.csv, Informe.html e Integrity.json.
El HTML muestra demanda, resumen y hasta 500 filas; el gráfico puede reducir
puntos para visualizar. JSON/CSV conservan todos los intervalos y los máximos
y energías se obtienen de la serie completa. No se sobrescribe un directorio
existente. Los hashes incluyen resultados y fuentes del adaptador compartido.
El circuito/workspace padre permanece intacto.

## Verificación reproducible

```powershell
python -m pytest tests/test_time_series.py tests/test_reactive_compensation.py tests/test_harmonics.py -q
python scripts/verify_time_series_mcp.py --output time_series_evidence
```

Se contrastan **16 combinaciones** de Daily/Yearly, 50/60 Hz, PQ/Z y pasos de
15/60 minutos; cada ejecución abarca 48 h. La referencia analítica de dos barras
es independiente del adaptador y contrasta tensión, corriente, kW/kvar,
demanda real, pérdidas y energía. También se ejecuta un script DSS nativo con
entradas independientes del constructor MCP. Las tolerancias están fijadas en
las pruebas: 2e-6 kW/kvar, 2e-7 pu, 2e-5 A y 2e-5 kWh en los casos de 48 h.

La prueba anual de 8.760 h utiliza un último punto distinto para comprobar el
extremo final y la demanda máxima; tolerancia energética 0.001 kWh. Otras
pruebas cubren perfiles de un punto, repetición autorizada, cargas múltiples,
transformador, rechazos, no convergencia, energía parcial bloqueada, hashes y
conservación del padre. El [registro Q7](evidence/time_series_q7_mcp.json) conserva errores, tolerancias
y hashes de fuentes. El transporte stdio realiza **39 llamadas MCP**, con los
16 casos y el ejemplo de dos cargas.

## Exclusiones y fuentes

No se integran reguladores, bancos automáticos, generadores, almacenamiento,
topologías cambiantes, desbalance, arranques dinámicos ni tarifas. ControlMode
está Off, LoadMult=1, Year=0 y crecimiento cero. Un perfil temporal de cargas
no sustituye un modelo EMT ni la dinámica de aceleración de motores.

Fuentes primarias:

- [EPRI — Time-based Simulations](https://opendss.epri.com/OpenDSSTime-basedSimulationsinMa.html).
- [EPRI — LoadShape](https://opendss.epri.com/LoadShape.html).
- [DSS-Extensions — LoadShape](https://dss-extensions.org/dss-format/LoadShape.html).
- [DSS-Extensions — Load](https://dss-extensions.org/dss-format/Load.html).
