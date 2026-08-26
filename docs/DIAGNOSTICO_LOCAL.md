# Diagnóstico local — MCP Eléctrico

`examples/diagnostico_local.py` es el **preflight del entorno local**. Su función es separar rápidamente un problema de Python/dependencias/OpenDSS/rutas de un problema del modelo eléctrico.

No sustituye:

- `examples/primer_uso.py`, que comprueba la integración completa y genera workspace;
- `examples/caso_referencia_01.py`, que compara OpenDSS con una referencia numérica independiente.

## Ejecución

Desde la raíz del repositorio y con el entorno virtual activado:

```bash
python examples/diagnostico_local.py
```

Por defecto genera:

```text
diagnostico_local.json
```

También puede elegirse otra ruta:

```bash
python examples/diagnostico_local.py --output salida/diagnostico_pc.json
```

## Estados

El script imprime una línea por chequeo y termina con uno de estos estados:

- `OK`: todos los chequeos esenciales y recomendados pasaron;
- `OK_WITH_WARNINGS`: el entorno puede continuar, pero existe al menos una advertencia no bloqueante;
- `FAIL`: falló al menos un chequeo esencial y el script termina con exit code `2`.

Una advertencia típica es ejecutar fuera de un `venv`. No impide el diagnóstico, pero sí aumenta el riesgo de mezclar `python` y `pip` de instalaciones distintas.

## Qué comprueba

El diagnóstico revisa explícitamente:

1. Python mínimo `3.11` y arquitectura de 64 bits.
2. Presencia de `server.py`, `requirements.txt` y `mcp_electrico/`.
3. Permiso de escritura en la carpeta del JSON.
4. Disponibilidad de Git como chequeo no bloqueante.
5. Instalación e import de:
   - `mcp`;
   - `opendssdirect.py`;
   - `pandapower`;
   - `networkx`.
6. Un circuito mínimo ejecutado **directamente con OpenDSSDirect**.
7. Un segundo flujo mínimo ejecutado mediante la **API pública `server.py`**.
8. La política determinista del eje E:
   - `automatic_dispatch=false`;
   - `crosscheck=false`;
   - OpenDSS como motor default actual;
   - pandapower como candidato preferente para IEC 60909;
   - IEC 60909 todavía `implemented=false`.
9. El gate formal de P3:
   - `READY_WITH_LIMITATIONS`;
   - `ready_for_next_phase=true`;
   - `next_phase=P4_IEC_60909`;
   - `professional_emission=false`.
10. La barrera de madurez:
    - `ampacity=VALIDATED_WITH_LIMITATIONS`;
    - `short_circuit=UNDER_VALIDATION`.

El diagnóstico **no ejecuta pandapower como solver**, no selecciona motores automáticamente y no realiza cross-check entre motores.

## Matriz rápida de fallos

| Resultado | Causa probable | Acción inicial |
|---|---|---|
| `python_version = FAIL` | Python demasiado antiguo | Instalar Python 3.11+ y recrear `venv` |
| `python_architecture = FAIL` | Python de 32 bits | Instalar Python de 64 bits |
| `package_* = FAIL` | Dependencias ausentes o `pip` distinto de `python` | `python -m pip install -r requirements.txt` |
| `opendss_direct_smoke = FAIL` | OpenDSSDirect/binario no operativo | Reinstalar dependencias en el mismo intérprete y conservar el JSON |
| `server_public_api = FAIL` | Clon incompleto, dependencia rota o revisión inconsistente | Confirmar rama/commit y ejecutar desde la raíz del repo |
| `output_write = FAIL` | Carpeta sin permisos | Elegir una carpeta local escribible |
| `engine_policy = FAIL` | Revisión incompatible con la matriz E esperada | No ejecutar estudios hasta revisar el commit |
| `p3_gate = FAIL` | Clon viejo/incompleto o datasets faltantes | Actualizar `main` y revisar archivos P3 |
| `maturity_barrier = FAIL` | Estado técnico inconsistente | No presentar FaultStudy como IEC 60909 |

## Secuencia recomendada después del clon

```bash
python examples/diagnostico_local.py
python examples/primer_uso.py
python examples/caso_referencia_01.py
```

La línea base esperada es:

```text
diagnostico_local  -> OK u OK_WITH_WARNINGS, con ok=true
primer_uso         -> ok=true
REF-01             -> pass=true
```

Si una prueba falla, conserva todos los JSON. Juntos permiten distinguir dependencia, motor, API pública, gate/madurez, integración visual y regresión numérica sin adivinar.

## Alcance y responsabilidad

Este diagnóstico solo verifica el entorno y contratos internos de la versión instalada. No valida un proyecto real, no ejecuta IEC 60909, coordinación/TCC ni IEEE 1584, y mantiene `professional_emission=false`.
