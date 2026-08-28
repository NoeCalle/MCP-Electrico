# P4-v1.1 — reingreso controlado de 2F-T

## Estado

**P4-v1.1A DONE — fundamento matemático 2F-T utilizable dentro del alcance declarado.**

P4-v1 cerró 2F-T como `OUT_OF_SCOPE_P4_V1` porque pandapower 3.5.4 no ofrece una API directa para falla bifásica a tierra. Ese cierre fue correcto para no aproximar silenciosamente 2F-T como 2F o 1F-T.

P4-v1.1 reabre el alcance mediante la segunda condición prevista en P4C08: **solver MCP dedicado de componentes simétricas**. El fundamento matemático ya dispone de benchmark independiente y auditoría adicional de condiciones de frontera. La integración automática con el modelo, la semántica IEC contractual y la revisión normativa siguen en gates separados.

## Estado de uso provisional

```text
mathematical_foundation = USABLE_WITH_DECLARED_SCOPE
model_integration       = PENDING_P4V11B
normative_verification  = PENDING_LICENSED_IEC_REVIEW
external_reference_case = PENDING
professional_emission   = false
```

Esto significa que el solver puede utilizarse como cálculo técnico interno cuando se proporcionan explícitamente `E1`, `Z1` y `Z0` compatibles con su alcance. No significa todavía que una salida 2F-T pueda etiquetarse automáticamente como `Ik''` IEC 60909 contractual ni que el MCP haya demostrado conformidad integral con IEC 60909-0:2026.

## Backend

Pandapower sigue siendo el backend previsto para obtener la red equivalente/impedancias de secuencia dentro del alcance ya soportado. El cálculo 2F-T no se presenta como una función nativa de pandapower.

```text
pandapower 3.5.4
  ├─ 3ph  soportado
  ├─ 2ph  soportado
  ├─ 1ph  soportado
  └─ 2ph-ground  NO soportado directamente
```

El solver MCP debe declarar siempre su origen y nunca etiquetar su resultado como `pandapower fault="2ph_ground"`.

## P4-v1.1A — fundamento matemático

Alcance:

- falla franca b-c-tierra;
- `Zf = 0`;
- componentes simétricas;
- `Z2 = Z1` únicamente para la red simétrica pasiva ya declarada por P4;
- `Z0` explícita;
- fuente positiva `E1` explícita;
- impedancias Thevenin pasivas con `R >= 0`, `X >= 0` y magnitud no nula;
- sin generadores, motores, convertidores ni modelos asimétricos.

Con falla franca 2F-T, la red positiva ve:

```text
Z1 + (Z2 || Z0)
```

y el solver calcula `I0`, `I1`, `I2`, reconstruye `Ia`, `Ib`, `Ic` y las tensiones de secuencia/fase.

Condiciones de frontera verificadas explícitamente:

```text
Ia = 0
Vb = 0
Vc = 0
I0 + I1 + I2 = 0
V0 = V1 = V2    en el nodo de falla bolted
Ia + Ib + Ic = 3 I0
```

En P4-v1.1A **no se promociona todavía** una magnitud contractual `Ik''` para 2F-T, ni `Sk''`, `ip` o `Ith`. La matemática puede utilizarse; la semántica IEC exacta se mantiene fail-closed hasta P4V11C/P4V11E.

## Auditoría matemática

La auditoría del fundamento incluye:

- comparación con la conexión clásica de redes de secuencia para doble línea a tierra;
- benchmark independiente que no repite directamente la fórmula del solver;
- resolución en dominio de fases mediante `Zabc` imponiendo `Ia=0`, `Vb=0`, `Vc=0`;
- casos deterministas BT y MT con distintas relaciones `Z0/Z1`;
- caso puramente resistivo permitido dentro del alcance pasivo;
- rechazo explícito de impedancias negativas/no pasivas;
- verificación de KCL, transformación de secuencias y condiciones de frontera de tensión.

Como comprobación adicional durante la auditoría se contrastaron múltiples combinaciones numéricas entre el solver de secuencias y la solución matricial en dominio de fases; no se detectó discrepancia material dentro de tolerancia numérica.

## Benchmark independiente

El benchmark construye `Zabc` desde `Z0/Z1/Z2`, resuelve directamente en dominio de fases las condiciones:

```text
Ia = 0
Vb = 0
Vc = 0
```

y compara corrientes de fase, corrientes de secuencia y tensiones de fase obtenidas.

Esto evita un test circular fórmula-contra-la-misma-fórmula.

## Gates de reingreso 2F-T

1. **P4V11A — matemática:** **DONE** — solver bolted + benchmark independiente + auditoría de invariantes.
2. **P4V11B — integración de modelo:** PENDIENTE — extracción trazable de `Z1/Z2/Z0` de la misma revisión del modelo y escenarios MAX/MIN.
3. **P4V11C — resultados:** PENDIENTE — contrato exacto de magnitudes 2F-T, unidades y semántica IEC; fail-closed para campos no cubiertos.
4. **P4V11D — benchmark de red:** PENDIENTE — caso reproducible con transformador, neutro y Z0 explícitos.
5. **P4V11E — revisión IEC 60909-0:2026:** PENDIENTE DIFERIDO — contraste específico contra el texto completo licenciado de la edición objetivo.
6. **P4V11F — Workspace V4:** PENDIENTE — representación 2F-T en la misma UI, sin cálculo JavaScript.
7. **P4V11G — gate de madurez:** PENDIENTE — actualización de `FAULT_SCOPE` solo después de los gates aplicables.

## VALIDACIONES PENDIENTES — registrar y no olvidar

Estas validaciones se mantienen explícitamente pendientes porque por el momento no están disponibles. **No invalidan el fundamento matemático P4V11A**, pero sí impiden afirmar verificación normativa integral o emisión profesional 2F-T.

### VP-2FT-01 — IEC 60909-0:2026 completa

Pendiente contrastar el método, factores aplicables y semántica exacta de resultados 2F-T contra el texto completo licenciado de IEC 60909-0:2026 Ed.3.

Estado: `PENDING_LICENSED_IEC_REVIEW`.

### VP-2FT-02 — caso externo de referencia

Pendiente comparar el resultado de una subestación/caso conocido contra una referencia externa independiente de confianza (estudio previamente aprobado, software comercial reconocido o benchmark publicado adecuado al mismo modelo).

Estado: `PENDING_EXTERNAL_REFERENCE_CASE`.

### VP-2FT-03 — revisión profesional del ingeniero

Antes de habilitar `professional_emission=true` para 2F-T, un ingeniero responsable debe revisar alcance, datos Z1/Z2/Z0, puesta a tierra, grupo vectorial, escenario MAX/MIN y correspondencia de resultados con la finalidad del estudio.

Estado: `PENDING_PROFESSIONAL_REVIEW`.

## Qué valida automáticamente el proyecto

- identidades matemáticas;
- benchmark independiente;
- condiciones `Ia=0`, `Vb=0`, `Vc=0`;
- KCL de secuencias;
- transformación secuencia ↔ fase;
- pasividad de impedancias dentro del alcance foundation;
- no aproximación 2F-T→2F/1F-T;
- regresiones P1–P5 existentes.

Los escenarios MAX/MIN, preservación automática de `Z0/Z1/Z2` desde el modelo y representación visual 2F-T pertenecen a gates posteriores.

## Políticas que permanecen

```text
professional_emission = false
automatic_dispatch = false
crosscheck = false
```

P5 continúa en paralelo; este trabajo no revierte ni invalida P4-v1 ya cerrado.
