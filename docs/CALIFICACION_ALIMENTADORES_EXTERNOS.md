# Calificación externa de redes de distribución publicadas

Banco preparado el 17 de octubre de 2026. La ejecución y sus resultados se registran
en la CI de la PR; solo una ejecución terminada permite afirmar el cierre del banco.

## Fuentes y separación de responsabilidades

Se usan las tablas numéricas de case33bw y case69 distribuidas con MATPOWER 8.1,
commit fijado `1a828c7af590714499284e36ee9c81273388c594`:
- [case33bw](https://github.com/MATPOWER/matpower/blob/1a828c7af590714499284e36ee9c81273388c594/data/case33bw.m), Baran y Wu, 1989, DOI 10.1109/61.25627.
- [case69](https://github.com/MATPOWER/matpower/blob/1a828c7af590714499284e36ee9c81273388c594/data/case69.m), Baran y Wu, 1989, DOI 10.1109/61.19265.

Los archivos de examples/qualification conservan hechos numéricos y atribución.
La licencia BSD del código MATPOWER no se atribuye a sus datos; consultar el aviso
del repositorio original. La CI descarga las fuentes por commit, compara todas
las tablas y la base MVA y registra SHA-256. No ejecuta código MATLAB descargado.

OpenDSS sigue siendo el ejecutor operativo. PYPOWER 5.1.21, referencia AC Newton
con tolerancia 1e-11 y máximo 100 iteraciones, se instala solo mediante el extra
`qualification`. Lee las tablas originales; no recibe tensiones o corrientes
de OpenDSS ni usa el adaptador pandapower del MCP. No se añade una segunda ruta
operativa ni un nuevo solver físico propio.

## Qué verifica el banco

| Comprobación | Cantidad y significado |
|---|---|
| Modelos completos del caso publicado | 33 y 69 barras, 32 y 68 ramas cerradas |
| Escenarios de carga | 50 %, 100 % y 125 %; solo el 100 % conserva las demandas originales |
| Flujo | Cada barra, corriente y P/Q de cada rama, pérdidas P/Q |
| Caída por línea | Diferencia de magnitudes relativa a la barra de origen, dentro del contrato existente |
| Contingencias | 100 aperturas simples, solución eléctrica, cargas sin tensión y restauración |
| Faltantes | Sin SCC de utility, Z0, ratings, conductor ni protecciones inventadas |
| Expediente | Entradas, referencia, resultados públicos MCP, comparación, netlist, versiones e integridad |

El cálculo independiente de conectividad comprueba qué cargas quedan aisladas
al abrir una rama. No sustituye el flujo eléctrico: cada contingencia llama al
ejecutor público y verifica la convergencia del modelo restaurado. Una prueba
de integración aprobada puede contener un criterio de suministro fallido: en
redes radiales sin respaldo las cargas aisladas pierden alimentación.

## Convenciones explícitas

Las fuentes publicadas fijan la tensión de la barra slack; no suministran una
potencia de cortocircuito de utility. Se representa con el modelo nativo OpenDSS
cuasiideal (`Model=Ideal`), base 10 MVA y R/X de 1e-8 pu; es una aproximación
numérica al límite de tensión fija. Se registra tolerancia 1e-10 y máximo 100
iteraciones. No es un equivalente físico de falla. FaultStudy queda bloqueado
para esta fuente y IEC conserva sus requisitos de SCC/revisión.

La representación usa cargas trifásicas equilibradas en estrella, PQ dentro de
un intervalo explícito de 0.5 a 1.5 pu. Estos límites se envían al motor como
Vminpu/Vmaxpu; fuera de ellos rige el comportamiento nativo OpenDSS. El banco
contrasta las soluciones dentro del intervalo y no califica colapso de tensión.

La frecuencia elegida es 60 Hz; las impedancias se suministran directamente en
ohmios. Las longitudes son equivalentes de una unidad con las R/X totales del
caso; no son metrajes físicos. Las cinco ramas abiertas de case33bw permanecen
fuera del modelo radial: no se añaden cierres ni se afirma reconfiguración.

Declarar todas las cargas como requeridas para la prueba de continuidad es un
criterio del banco; no se atribuye una clasificación de criticidad a los autores.
Los ratings no publicados no se sustituyen por los valores internos de OpenDSS.

## Tolerancias fijadas antes de ejecutar

| Magnitud pública | Tolerancia absoluta |
|---|---|
| Tensión | 0.0002 pu |
| Pérdidas P/Q | 0.05 kW / kvar |
| Corriente de rama | 0.05 A |
| Potencia de rama P/Q | 0.05 kW / kvar |
| Caída de tensión | 0.03 puntos porcentuales |

Las tolerancias incluyen el redondeo de presentación público (4 decimales para
tensiones, 3 para potencias/corrientes) y el error numérico. Se exige cumplir
cada comparación; no se reemplaza un error absoluto por otro relativo más laxo.
El expediente conserva errores máximos y los valores completos para auditarlos.

Se registra además una ejecución con la representación anterior, que conserva
la impedancia interna de fuente y el rango PQ por defecto del motor. Es un
diagnóstico de traducción de datos, no una acusación de error del solver: un
modelo distinto puede dar resultados distintos aun cuando ambos converjan.

## Límites de lo que puede concluirse

Este banco amplía evidencia externa para flujo equilibrado PQ y contingencias
radiales explícitas. No valida transformadores, desbalance, redes malladas,
variadores, coordinación integral, estabilidad ni dinámica de redes completas.
Tampoco convierte un benchmark publicado en un proyecto de cliente aprobado
ni acredita una cobertura del 90 % de estudios.

El siguiente escalón de proyecto real requiere un expediente con datos trazables
de fuente, transformadores, cables, protecciones y cargas; sin ese expediente,
los módulos correspondientes deben seguir indicando los datos faltantes.

## Reproducción

```bash
python -m pip install -e ".[dev,qualification]"
python -m pytest tests/test_external_feeder_qualification.py -q
python scripts/verify_external_feeders_mcp.py --output outputs/external-feeders --verify-upstream
```

El directorio de salida debe ser nuevo. Evidence.json registra estados,
versiones y fuentes; Integrity.json inventaría los archivos, entradas, resultados,
referencias y netlist. MCP-stderr.log es un registro de diagnóstico separado.
