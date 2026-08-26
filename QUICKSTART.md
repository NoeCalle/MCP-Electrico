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

## 3. Qué comprueba

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

## 5. Qué NO demuestra

Este smoke test no es un estudio eléctrico profesional ni una validación de un proyecto real. El caso usa parámetros deliberadamente simples para probar que toda la cadena funciona.

En particular:

- el límite de caída de tensión de 3 % es un parámetro del ejemplo, no una regla universal;
- no ejecuta IEC 60909;
- no ejecuta coordinación/TCC;
- no ejecuta IEEE 1584;
- no habilita `professional_emission` del resultado global.

## 6. Si falla

El script sale con código distinto de cero cuando algún chequeo esencial falla. Conserva la salida de consola y el JSON si llegó a generarse: ambos sirven para identificar si el problema está en dependencias, OpenDSS, el gate de madurez o la generación visual.

Una vez que este smoke test pase localmente, el siguiente paso recomendado es probar un caso real pequeño y comparar sus magnitudes con una referencia independiente antes de escalar a redes mayores.
