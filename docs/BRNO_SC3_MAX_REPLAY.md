# Brno: reproducción de corriente inicial trifásica máxima

## Estado y alcance

Se reproduce el informe público `Untitled.SI1S` del mismo ZIP fijado en
`examples/qualification/brno_industrial_2026.json`. Son **11 barras publicadas,
8 nodos eléctricos distintos** después de fusionar enlaces exportados con
impedancia cero. Se incluyen 73 grupos de inducción equivalentes de la
configuración normal. Los generadores Gen1/Gen2 están en componentes separados
y no se incorporan al componente de red estudiado.

Esto valida la traducción de **Ik'' inicial, 3F, máximo**, contra el modelo
académico publicado. No es una medición de planta ni una validación integral
de la instalación. No se calculan/reconstruyen MIN, Ib/Ik de decaimiento,
Ith con máquinas, tierra compensada ni protecciones. No se afirma conformidad
integral con la edición objetivo de IEC 60909.

## Entradas y comparación

- Se leen en SQLite inmutable las entradas IBus/IConnect/Icable/IXFMR2,
  IUtility, ILump, ISynGen e ISCStudyCase.
- Las referencias son únicamente los totales iniciales `SCIEC3ph.kAMag`,
  contrastados con `SCIEC3phSum.IPPk` de cada barra. No se confunden con
  `ip`, `Ik` o `Ith`; el informe conserva magnitudes distintas.
- Cables a 20 °C, longitudes en metros convertidas a km y paralelos
  explícitos. Se retienen datos publicados de transformadores y tap nominal
  fijo. La rama homopolar BT conflictiva queda fuera del alcance: no se
  deduce su puesta a tierra desde D/Y ni se califica una falla a tierra.
- `IUtility.MVA3ph=171.4730224609375` MVA y X/R=10 se pasan **sin modificar**.
  Las columnas R/X exportadas son una comprobación de consistencia nominal,
  no sustituyen la corrección IEC nativa de la potencia Scc.
- El informe usa factor BT 1.05. La opción nativa `lv_tol_percent=6`
  de pandapower 3.5.4 lo selecciona; la opción 10 mantiene 1.10.
- Para cada grupo: Sn = kVA nominal × fracción MTR, y Z bloqueada =
  (R+jXppIEC)% sobre esa Sn. No se usa la potencia operativa como potencia
  mecánica nominal ni se atribuyen placas individuales.

El script de investigación conserva también la interpretación alternativa de
la impedancia exportada **sin corrección IEC**: produce diferencias
0.636–0.966%. Se conserva para explicar la ambigüedad, no como parámetro
calibrado para ajustar una referencia.

La traducción literal de Scc, con el resto de entradas publicadas, obtiene
una diferencia máxima relativa aproximada de **7.45e-8** en las 11 barras.
La aceptación de la prueba MCP exige error relativo <= 1e-4 (0.01%),
corrientes positivas y finitas, cobertura completa y preservación del alcance.

## Contratos nuevos del MCP

### Grupo equivalente explícito

`definir_grupo_motores_equivalente_3ph` admite un Load existente y trifásico,
Sn nominal, tensión nominal, R%/X% bloqueadas y referencia. Guarda
`GRUPO_INDUCCION_EQUIVALENTE`; no lo convierte en una placa individual.

La parametrización interna del backend usa pn=Sn, eta=1 y cosphi=1 para
preservar Sn y Z en el modelo nativo de cortocircuito. Son coordenadas del
adaptador, **no datos de rendimiento/factor de potencia de un motor real**.
El backend ejecuta las ecuaciones; el MCP no añade otro solver.
Las entradas y magnitudes derivadas deben ser finitas; X>0, Sn>0, V>0 y
la corriente bloqueada debe ser >=1 pu.

Continúan los gates de tensión, estado/conectividad y clasificación de todas
las cargas. Con grupos se rechaza ip/Ith por la misma limitación de máquinas;
MIN excluye su contribución si se solicita con sus datos y temperaturas.
Los variadores no se aproximan como grupos de inducción.

### Selección explícita del escenario y del factor BT

`evaluar_preparacion_cortocircuito_3ph` y
`ejecutar_cortocircuito_iec60909_3ph` reciben:

- `caso="max_min"` por defecto, o `"max"` / `"min"`.
- `lv_tol_percent=10` por defecto, o `6`.

Ambos parámetros forman parte de la huella del control previo: cambiar
caso o tolerancia invalida una revisión anterior. Sin revisión válida no se
llama al solver. Un MAX explícito no exige inventar una fuente MIN;
solicitar la pareja completa sigue fallando si falta MIN. MIN conserva su
exigencia de temperatura por cable.

El resultado de escenario único enumera `requested_cases`,
`omitted_cases` y `max_min_pair_complete=false`. No satisface el gate
P8 que exige la pareja MAX/MIN. La vista muestra el escenario omitido
como **NO SOLICITADO**, sin corriente inventada. El contrato previo por
defecto sigue ejecutando MAX/MIN y no cambia su factor.

La ruta general `ejecutar_estudio(estudio="iec60909",
tipo_falla="three_phase", parametros=...)` utiliza el mismo ejecutor y
sus gates; la matriz selecciona únicamente pandapower para este estudio.
No hay fallback ni comparación con un segundo motor en ejecución.

## Repetición y evidencia

```powershell
python -m pytest tests/test_sc3_group_scenarios.py tests/test_sc_machines.py -q
python scripts/replay_brno_sc3_research.py
python scripts/verify_brno_sc3_mcp.py
```

El workflow `brno-sc3-research` ejecuta Windows/Linux. La prueba pública
construye la red mediante tools y utiliza Load de P=Q=0 solo como puertos de
las fichas SC: **no reconstruye la demanda de flujo ni ejecuta power flow**.
La demanda estática no aporta corriente en este método de fuente equivalente.

Por sistema se conservan entradas derivadas, comparación por barra,
424 llamadas MCP y resultados por rama. Se comprueban la revisión obligatoria,
el rechazo de MAX/MIN sin fuente MIN, los equivalentes y el enrutamiento.
No se modifica ni redistribuye el ZIP original.

Pendientes: fuente y temperaturas MIN trazables, referencia homóloga MIN,
reconciliación LF/SC de una revisión común, tierra, curvas/unidades y capacidad
de todos los dispositivos participantes; decaimiento/Ith con máquinas cuando
se amplíe y califique ese alcance. `installation_validation_closed=false`
y `field_validation_performed=false` permanecen explícitos.

## Validación que continúa con los datos disponibles

La ausencia de una fuente MIN autenticada no detiene la validación del MCP.
El replay público amplía cada una de las 11 barras con una variante explícita
`lv_tol_percent=10` y un retorno al ajuste publicado `6`:

- la revisión del ajuste 6 debe rechazarse al solicitar 10;
- cada variante se revisa con su propia huella y usa solo pandapower;
- volver a 6 debe recuperar la misma huella y corriente, con diferencia
  relativa <= 1e-10;
- las corrientes de sensibilidad deben ser positivas y finitas;
- los artefactos conservan entradas, revisiones, corrientes y variación relativa.

La variante 10 es una prueba de sensibilidad del software. No tiene una
referencia externa propia, no representa una condición confirmada de la planta
y no se denomina escenario mínimo. El contraste externo sigue correspondiendo
exclusivamente al ajuste publicado 6. No se exige una variación prefijada de
corriente: los factores también intervienen en correcciones nativas de equipos.

El trabajo continúa por alcance: contraste externo MAX, repetibilidad y controles
de revisión sobre Brno; MIN mediante bancos con entradas explícitas; protección
mediante curvas y ejemplos con semántica documentada. Los datos faltantes de
Brno afectan al cierre de ese proyecto, no bloquean esas validaciones. No se
completan por inferencia la fuente MIN, temperaturas ni tiempos de disparo.
