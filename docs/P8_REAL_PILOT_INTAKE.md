# P8B — Admisión del piloto real

## Objetivo

P8A ya demostró la ruta completa de MCP Eléctrico 0.9 sobre una subestación sintética técnicamente realista. P8B prepara el ingreso del **primer proyecto real** sin inventar datos y sin confundir presencia documental con aptitud eléctrica.

P8B es un gate previo al modelado:

```text
manifest de proyecto
        ↓
P8B — presencia + trazabilidad + plausibilidad básica
        ↓
READY_TO_BUILD_MODEL
        ↓
construcción mediante tools MCP
        ↓
gates P2/P3/P4/P5 del modelo real
        ↓
Workspace V5
        ↓
P7A snapshot + P7C reporte
```

## Lo que P8B NO hace

```text
electrical_calculation = false
model_mutation = false
automatic_defaults = false
automatic_dispatch = false
crosscheck = false
professional_emission = false
```

`READY_TO_BUILD_MODEL` **no** significa `READY_TO_EXECUTE`, cumplimiento normativo integral ni autorización de emisión. Solo significa que el paquete de entrada contiene los campos solicitados y supera controles básicos de plausibilidad. La coherencia y suficiencia técnica se vuelven a evaluar después con P2/P3/P4/P5.

## Alcance admitido

```text
POWER_FLOW
VOLTAGE_DROP
AMPACITY
IEC60909_3PH_MAX_MIN
IEC60909_1PH_GROUND_MAX_MIN
PROTECTION_TCC
```

IEEE 1584 permanece fuera de P8B:

```text
P6_IEEE1584_ARC_FLASH = DEFERRED
```

Cualquier scope no soportado falla cerrado.

## Información base del proyecto

El manifiesto exige como mínimo:

- identificador y nombre del proyecto/subestación;
- referencia de procedencia: SLD, expediente, plano, memoria o revisión identificable;
- barra explícita de conexión de la fuente aguas arriba;
- tensión nominal de la red aguas arriba;
- barras del alcance;
- transformadores;
- líneas/cables;
- cargas.

La plantilla está en:

`examples/p8b_real_pilot_manifest_template.json`

## Topología construible — gate común

P8B no considera suficiente que las listas de topología sean simplemente no vacías. Antes de declarar `READY_TO_BUILD_MODEL` comprueba un mínimo estructural para evitar un falso verde en `POWER_FLOW` o `VOLTAGE_DROP`:

- `source.bus` debe existir en `topology.buses`;
- IDs de barras no vacíos y únicos;
- cada transformador referencia barras declaradas y aporta potencia, tensiones, uk%, grupo vectorial y X/R o pérdidas de carga;
- cada línea/cable declara barras de origen/destino, fases, longitud, R1 y X1;
- cada carga declara barra, fases, tensión, kW y kvar;
- las referencias de barras deben resolver contra `topology.buses`;
- los IDs de elementos deben ser únicos en la topología;
- el conjunto del alcance debe ser conexo desde `source.bus`;
- fichas Z0, ampacidad y protección deben referenciar elementos realmente presentes en la topología.

Estos controles siguen siendo **pre-modelado**: no compilan OpenDSS, no ejecutan flujo y no sustituyen el QA P2–P5.

`base_model_readiness` expone por separado estos blockers comunes. Cada `study_input_readiness` incorpora también los blockers del modelo base, de modo que un estudio nunca aparezca `INPUTS_PRESENT` si la topología que necesita todavía no puede construirse.

## IEC 60909 3F MAX/MIN

Para solicitar `IEC60909_3PH_MAX_MIN`, P8B exige además:

- Scc3 MAX y X/R MAX;
- Scc3 MIN y X/R MIN;
- temperatura final MIN explícita por línea/cable.

No se inventa temperatura para el escenario mínimo.

## IEC 60909 1F-T MAX/MIN

Además de la secuencia positiva y la temperatura MIN, exige:

- R0/X0 MAX y MIN de la fuente;
- R0/X0/C0 de todas las líneas/cables incluidas en el alcance;
- ficha Z0 de todos los transformadores del alcance;
- lado y modo de neutro/puesta a tierra;
- IDs Z0 vinculados a elementos existentes del modelo positivo.

La disponibilidad de Scc3 no se interpreta como disponibilidad de Z0. Si el alcance contiene un elemento sin ficha homopolar, P8B bloquea el ingreso en vez de asumirla.

## Ampacidad P3

Para cada elemento incluido se solicita:

- elemento existente de la topología;
- conductor identificado;
- Ib;
- In;
- referencia de instalación;
- referencia de ampacidad/dataset aplicable.

P8B no calcula `Iz` ni selecciona tablas: eso sigue perteneciendo a P3 y a su evidencia normativa exacta.

## Protección/TCC P5

Se requieren dispositivos con:

- identidad;
- tipo;
- elemento protegido existente en la topología;
- In;
- Ue;
- capacidad de corte;
- referencia documental.

Los datasets TCC deben identificar:

- dataset;
- semántica de tiempo;
- tipo de fuente;
- referencia documental.

P8B no digitaliza curvas ni crea ajustes.

## Plausibilidad básica

P8B rechaza valores evidentemente imposibles antes del modelado:

- tensiones, Scc, X/R, potencias nominales y longitudes no positivas;
- R/X/Z0 negativos dentro del alcance pasivo actual;
- kW negativos para cargas pasivas;
- ratings de protección no positivos;
- referencias a barras o elementos inexistentes;
- islas topológicas no conectadas a la fuente declarada.

Esto no sustituye el QA eléctrico posterior.

## Uso por CLI

```bash
python examples/evaluate_p8b_real_pilot_intake.py \
  --input proyecto_real.json \
  --output admision_p8b.json
```

También está disponible como tool MCP mediante `evaluar_admision_piloto_real`.

## Regla de evidencia

Los valores sintéticos del piloto P8A **no deben copiarse** a un proyecto real. Fuente equivalente, Z0, transformadores, cables, cargas, instalación, protecciones y curvas deben reemplazarse por datos del expediente/proveedor/concesionaria correspondiente y conservar su referencia.
