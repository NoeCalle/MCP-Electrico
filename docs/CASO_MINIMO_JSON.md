# Caso mínimo JSON V1

`MCP_ELECTRICO_MINIMAL_CASE_V1` es el primer formato editable pensado para pasar de las pruebas de instalación a un **caso eléctrico pequeño definido por datos**, sin modificar código Python.

El alcance es deliberadamente estrecho para mantenerse cerca de la validación P1 actual:

- red radial;
- trifásica balanceada;
- una sola tensión nominal línea-línea;
- líneas serie y cargas PQ;
- OpenDSS como motor explícito;
- flujo de potencia + caída de tensión + workspace persistente.

V1 **no** admite transformadores, generadores, lazos, desbalance, secuencia cero, ampacidad P3 automática, IEC 60909, coordinación/TCC ni IEEE 1584.

## Uso

Copiar la plantilla:

```text
examples/caso_minimo.json
```

Editar sus valores y ejecutar:

```bash
python examples/ejecutar_caso_minimo.py mi_caso.json --output-dir salida_mi_caso
```

Si se omite el archivo, se usa la plantilla incluida:

```bash
python examples/ejecutar_caso_minimo.py
```

## Salidas

La carpeta de salida contiene:

```text
workspace_caso_minimo.html
caso_entrada_normalizado.json
resultado_caso_minimo.json
```

`caso_entrada_normalizado.json` es la entrada después de validación y normalización. Su contenido canónico se hashea con SHA-256 y el digest queda registrado en `resultado_caso_minimo.json` como `input_sha256`.

Esto permite saber exactamente qué entrada produjo un resultado.

## Estructura

### `project`

```json
{
  "id": "CASO_BT_01",
  "title": "Caso BT",
  "notes": "texto opcional"
}
```

`id` y los nombres internos solo admiten letras, números, guion y guion bajo, iniciando con una letra. Esta restricción evita nombres ambiguos o inseguros al construir comandos OpenDSS.

### `circuit`

```json
{
  "name": "caso_bt_01",
  "base_kv_ll": 0.48,
  "frequency_hz": 60,
  "source_bus": "sourcebus"
}
```

En V1:

- `source_bus` debe ser exactamente `sourcebus`;
- `frequency_hz` solo puede ser 50 o 60;
- toda la red usa `base_kv_ll`;
- no se permite cambio de nivel de tensión.

### `lines`

Cada línea debe aparecer **en orden aguas abajo**. `bus1` debe existir antes de crear la línea y `bus2` debe ser nuevo.

```json
{
  "name": "f_panel_a",
  "bus1": "sourcebus",
  "bus2": "panel_a",
  "length_km": 0.06,
  "r1_ohm_km": 0.2,
  "x1_ohm_km": 0.08,
  "visual": {
    "label": "F-01",
    "protection": "mccb",
    "conductor": "3x70 mm2 Cu XLPE",
    "nominal_current_a": 160,
    "breaking_capacity_ka": 25
  }
}
```

La regla `bus2 nuevo` impide lazos y reconexiones en V1. Las ramas sí están permitidas: varias líneas pueden partir de un mismo bus ya conocido.

Los campos de `visual` no modifican la impedancia ni el cálculo; solo enriquecen el workspace.

### `loads`

```json
{
  "name": "carga_panel_a",
  "bus": "panel_a",
  "kw": 40,
  "kvar": 15,
  "visual": {
    "label": "TABLERO A",
    "type": "tablero",
    "critical": false
  }
}
```

La carga debe conectarse a un bus que ya pertenezca al árbol. V1 la crea siempre como carga trifásica al mismo `base_kv_ll` del circuito.

Tipos visuales admitidos actualmente: `tablero`, `motor`, `carga`.

### `study`

```json
{
  "voltage_drop_limit_pct": 3.0
}
```

El límite es **configurable por el usuario**. El MCP no afirma que 3 % sea un requisito normativo universal.

## Fail-closed

El loader rechaza el caso antes de ejecutar OpenDSS cuando encuentra, entre otros:

- schema distinto de `MCP_ELECTRICO_MINIMAL_CASE_V1`;
- campos desconocidos;
- nombres duplicados o inválidos;
- bus de origen todavía inexistente;
- intento de conectar una línea a un `bus2` ya existente;
- carga conectada fuera del árbol;
- longitudes o resistencias no positivas;
- protección o tipo visual no admitido;
- frecuencia distinta de 50/60 Hz.

No existe interpolación, corrección automática ni intento de “adivinar” la intención del usuario.

## Política de motores

La ejecución V1 registra explícitamente:

```text
executed_engine = OpenDSS
automatic_dispatch = false
crosscheck = false
pandapower_executed = false
```

El formato no llama a pandapower ni a FaultStudy.

## Secuencia recomendada

Antes de usar un JSON editado:

```bash
python examples/diagnostico_local.py
python examples/primer_uso.py
python examples/caso_referencia_01.py
```

Luego:

```bash
python examples/ejecutar_caso_minimo.py mi_caso.json --output-dir salida_mi_caso
```

## Alcance profesional

El resultado mantiene `professional_emission=false`. Tener flujo convergente y un workspace correcto no convierte automáticamente el caso en un estudio profesional. Para un proyecto real siguen siendo necesarios datos trazables, revisión de ingeniería, QA y los módulos normativos correspondientes.
