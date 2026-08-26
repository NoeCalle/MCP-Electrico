# MCP Eléctrico — Primer uso

Este quickstart está pensado para el **primer clon local** del repositorio. Antes de probar casos reales, ejecuta un smoke test integral que comprueba instalación, OpenDSS, madurez declarada, gate P3, flujo de potencia, caída de tensión y generación del workspace.

## 1. Crear entorno

```bash
git clone https://github.com/NoeCalle/MCP-Electrico.git
cd MCP-Electrico
python -m venv venv
```

Windows:

```powershell
venv\Scripts\activate
pip install -r requirements.txt
```

Linux/macOS:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

## 2. Ejecutar el primer smoke test

```bash
python examples/primer_uso.py
```

Una ejecución sana termina con `"ok": true` y **exit code 0**. Si falla algún chequeo esencial, el script termina con código distinto de cero.

Por defecto se crea:

```text
salida_primer_uso/
├── workspace_primer_uso.html
└── resultado_primer_uso.json
```

También puedes elegir otra carpeta:

```bash
python examples/primer_uso.py --output-dir mi_prueba
```

## 3. Qué comprueba el smoke

El resultado debe terminar con `"ok": true` y verifica de forma explícita:

- OpenDSS converge para una red pequeña 22.9/0.48 kV;
- se genera el workspace HTML persistente;
- P3-v1 está cerrada como `READY_WITH_LIMITATIONS`;
- `ampacity` está en `VALIDATED_WITH_LIMITATIONS`;
- P4 IEC 60909 está formalmente habilitada como siguiente fase;
- `short_circuit` sigue `UNDER_VALIDATION`, por lo que no se presenta el actual FaultStudy como IEC 60909;
- `automatic_dispatch=false` y `crosscheck=false`;
- pandapower no se ejecuta silenciosamente durante este smoke test.

## 4. Qué resultados mirar primero

En `resultado_primer_uso.json` revisa:

```text
checks
runtime
engine_policy
maturity
p3_gate
power_flow
voltage_drop
outputs
```

El criterio configurado de caída de tensión queda explícito en `voltage_drop.criterio.limite_pct`; el mismo bloque declara `origen=configurable_por_usuario` y `normativo_universal=false`.

En `workspace_primer_uso.html` revisa el unifilar, el inspector y las vistas de flujo, caída de tensión y ampacidad disponibles en el workspace.

## 5. Segundo paso: comprobar números contra REF-01

Después de que el smoke pase, ejecuta el primer patrón oro numérico:

```bash
python examples/caso_referencia_01.py
```

Genera `resultado_caso_referencia_01.json`. REF-01 es una red radial trifásica balanceada de 480 V con una línea de 0.1 km y una carga PQ de 80 kW + 40 kvar. La solución de referencia se obtiene mediante una iteración compleja independiente de dos barras y sus valores esperados están congelados en `mcp_electrico/data/reference_case_01.json`.

Magnitudes de referencia aproximadas:

```text
V receptor = 0.987694 pu
I          = 108.923 A
Pérdidas P = 1.06778 kW
Pérdidas Q = 0.35593 kvar
ΔV         = 1.23057 %
```

El script comprueba simultáneamente que:

- la solución analítica recalculada sigue coincidiendo con el patrón congelado;
- las tolerancias coinciden con las tolerancias P1 publicadas;
- OpenDSS permanece dentro de tolerancia para tensión, corriente, pérdidas P/Q y caída de tensión.

Una ejecución sana devuelve `"pass": true` y exit code 0. Esta comparación es deliberadamente independiente: los valores de referencia congelados **no dependen de OpenDSS**.

## 6. Qué NO demuestran estas pruebas

Ni el smoke ni REF-01 son estudios eléctricos profesionales ni validaciones de un proyecto real. Son pruebas reproducibles de instalación, integración y regresión numérica.

En particular:

- el límite de caída de tensión de 3 % del smoke es un parámetro del ejemplo, no una regla universal;
- REF-01 cubre únicamente un sistema radial trifásico balanceado de dos barras;
- el smoke no ejecuta IEC 60909 y REF-01 tampoco;
- no ejecutan coordinación/TCC;
- no ejecutan IEEE 1584;
- no habilitan `professional_emission` del resultado global.

## 7. Si algo falla

Los scripts terminan con código distinto de cero cuando un chequeo esencial falla. Conserva la salida de consola y los JSON generados: sirven para diferenciar un problema de dependencias, OpenDSS, madurez/gates, postproceso o regresión numérica.

Con **primer_uso = OK** y **REF-01 = PASS**, el entorno local queda en una buena línea base para empezar con un caso real pequeño y comparar después sus magnitudes con una referencia independiente antes de escalar a redes mayores.
