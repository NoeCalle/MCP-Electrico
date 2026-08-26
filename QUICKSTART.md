# MCP Eléctrico — Primer uso

Este quickstart está pensado para el **primer clon local** del repositorio. Antes de probar casos reales, la secuencia recomendada separa diagnóstico del entorno, smoke de integración, patrón numérico independiente y, recién después, un caso editable definido por datos.

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

## 2. Diagnóstico local antes del smoke

```bash
python examples/diagnostico_local.py
```

Genera `diagnostico_local.json`. Una instalación apta para continuar debe devolver `ok=true` y `overall_status=OK` u `OK_WITH_WARNINGS`. Un `WARN` es no bloqueante; un chequeo esencial en `FAIL` termina con exit code 2.

Este preflight verifica Python/arquitectura, dependencias, OpenDSSDirect, API pública `server.py`, permisos de escritura, gate P3 y la matriz determinista de motores. No ejecuta pandapower como solver, conserva `automatic_dispatch=false` y `crosscheck=false`, y confirma que el MCP todavía **no ejecuta IEC 60909** como módulo validado.

La explicación completa y matriz de fallos está en `docs/DIAGNOSTICO_LOCAL.md`.

## 3. Ejecutar el primer smoke test

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

## 4. Qué comprueba el smoke

El resultado debe terminar con `"ok": true` y verifica de forma explícita:

- OpenDSS converge para una red pequeña 22.9/0.48 kV;
- se genera el workspace HTML persistente;
- P3-v1 está cerrada como `READY_WITH_LIMITATIONS`;
- `ampacity` está en `VALIDATED_WITH_LIMITATIONS`;
- P4 IEC 60909 está formalmente habilitada como siguiente fase;
- `short_circuit` sigue `UNDER_VALIDATION`, por lo que no se presenta el actual FaultStudy como IEC 60909;
- `automatic_dispatch=false` y `crosscheck=false`;
- pandapower no se ejecuta silenciosamente durante este smoke test.

## 5. Qué resultados mirar primero

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

## 6. Tercer paso: comprobar números contra REF-01

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

## 7. Cuarto paso: ejecutar el primer caso JSON editable

Con diagnóstico, smoke y REF-01 en verde, ya se puede pasar a una red pequeña definida sin editar Python:

```bash
python examples/ejecutar_caso_minimo.py
```

El comando usa `examples/caso_minimo.json`. Para trabajar sobre una copia:

```bash
python examples/ejecutar_caso_minimo.py mi_caso.json --output-dir salida_mi_caso
```

La carpeta genera:

```text
workspace_caso_minimo.html
caso_entrada_normalizado.json
resultado_caso_minimo.json
```

`caso_entrada_normalizado.json` conserva la entrada efectiva después de validarla; su representación canónica recibe un SHA-256 que queda escrito como `input_sha256` en el resultado. Así el flujo, la caída de tensión y el workspace quedan vinculados a una entrada concreta y reproducible.

El formato `MCP_ELECTRICO_MINIMAL_CASE_V1` es deliberadamente fail-closed: solo admite red radial trifásica balanceada de una sola tensión, con líneas y cargas PQ. No admite transformadores, generadores, lazos, desbalance ni secuencia cero. Mantiene OpenDSS explícito, `automatic_dispatch=false`, `crosscheck=false` y `pandapower_executed=false`.

La especificación completa y los campos editables están en `docs/CASO_MINIMO_JSON.md`.

## 8. Qué NO demuestran estas pruebas ni el caso mínimo

El diagnóstico, el smoke, REF-01 y el caso JSON V1 no son por sí solos estudios eléctricos profesionales ni validaciones de un proyecto real. Son una cadena reproducible para comprobar entorno, integración, regresión numérica y una primera entrada declarativa controlada.

En particular:

- el límite de caída de tensión de 3 % del smoke y de la plantilla es un parámetro configurable, no una regla universal;
- REF-01 cubre únicamente un sistema radial trifásico balanceado de dos barras;
- el diagnóstico y el smoke no ejecutan IEC 60909 y el caso mínimo tampoco;
- el caso mínimo V1 no ejecuta ampacidad normativa P3 automáticamente;
- no ejecutan coordinación/TCC;
- no ejecutan IEEE 1584;
- no habilitan `professional_emission` del resultado global.

## 9. Si algo falla

Los scripts terminan con código distinto de cero cuando un chequeo esencial falla. Conserva la salida de consola y los JSON generados: sirven para diferenciar un problema de dependencias, OpenDSS, API pública, madurez/gates, validación de entrada, postproceso, generación visual o regresión numérica.

La línea base antes de escalar a modelos más completos queda así:

```text
diagnostico_local -> OK u OK_WITH_WARNINGS, con ok=true
primer_uso        -> ok=true
REF-01            -> pass=true
caso_minimo       -> ok=true
```

Con los cuatro pasos en verde, ya existe una base controlada para empezar a sustituir la plantilla por datos de un caso real pequeño, conservando siempre la revisión de ingeniería y sin saltarnos los límites publicados del roadmap.

## 10. Atajo: validar toda la línea base con un comando

Si se quiere ejecutar los cuatro pasos anteriores de forma aislada pero orquestada, usar:

```bash
python examples/validar_linea_base.py
```

El comando crea `salida_validacion_local/`, ejecuta cada etapa en un proceso Python separado y genera `manifiesto_linea_base.json`. El resultado esperado es `status=PASS`, con `passed=4` y `failed=0`.

El manifiesto registra el commit Git disponible, schemas, códigos de retorno, artefactos y sus SHA-256. El orquestador no añade lógica eléctrica, mantiene `automatic_dispatch=false`, `crosscheck=false` y `professional_emission=false`. Los hashes identifican los archivos de una ejecución; no sustituyen a REF-01 como criterio de equivalencia numérica entre equipos.

La especificación completa está en `docs/VALIDACION_LINEA_BASE_LOCAL.md`.
