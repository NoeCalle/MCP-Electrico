# P4-v1.1 — reingreso controlado de 2F-T

## Estado

**P4-v1.1A EN DESARROLLO — fundamento matemático 2F-T.**

P4-v1 cerró 2F-T como `OUT_OF_SCOPE_P4_V1` porque pandapower 3.5.4 no ofrece una API directa para falla bifásica a tierra. Ese cierre fue correcto para no aproximar silenciosamente 2F-T como 2F o 1F-T.

P4-v1.1 reabre el alcance únicamente mediante la segunda condición prevista en P4C08: **solver MCP dedicado de componentes simétricas**, con contrato, benchmark independiente, CI, revisión normativa y representación visual antes de promover la falla.

## Backend

Pandapower sigue siendo el backend para obtener la red equivalente/impedancias de secuencia dentro del alcance ya soportado. El cálculo 2F-T no se presenta como una función nativa de pandapower.

```text
pandapower 3.5.4
  ├─ 3ph  soportado
  ├─ 2ph  soportado
  ├─ 1ph  soportado
  └─ 2ph-ground  NO soportado directamente
```

El solver MCP debe declarar siempre su origen y nunca etiquetar su resultado como `pandapower fault="2ph_ground"`.

## P4-v1.1A — fundamento matemático

Alcance inicial:

- falla franca b-c-tierra;
- `Zf = 0`;
- componentes simétricas;
- `Z2 = Z1` únicamente para la red simétrica pasiva ya declarada por P4;
- `Z0` explícita;
- fuente positiva `E1` explícita;
- sin generadores, motores, convertidores ni modelos asimétricos.

Con falla franca 2F-T, la red positiva ve:

```text
Z1 + (Z2 || Z0)
```

y el solver calcula `I0`, `I1`, `I2`, reconstruye `Ia`, `Ib`, `Ic` y verifica `Ia≈0` y `Ia+Ib+Ic=3I0`.

En P4-v1.1A **no se promociona todavía** una magnitud contractual `Ik''` para 2F-T, ni `Sk''`, `ip` o `Ith`. Primero se valida la matemática y posteriormente se revisa la semántica exacta de resultados contra IEC 60909-0:2026.

## Benchmark independiente

El benchmark no repite la fórmula de secuencias del solver. Construye `Zabc` desde `Z0/Z1/Z2`, resuelve directamente en dominio de fases las condiciones:

```text
Ia = 0
Vb = 0
Vc = 0
```

y compara las corrientes de fase y de secuencia obtenidas.

Esto evita un test circular fórmula-contra-la-misma-fórmula.

## Gates de reingreso 2F-T

2F-T solo podrá pasar de `OUT_OF_SCOPE_P4_V1` a un alcance P4-v1.1 cuando se cumplan todos los siguientes:

1. **P4V11A — matemática:** solver de secuencias bolted + benchmark independiente PASS.
2. **P4V11B — integración de modelo:** extracción trazable de `Z1/Z2/Z0` de la misma revisión del modelo y escenarios MAX/MIN.
3. **P4V11C — resultados:** contrato exacto de magnitudes 2F-T, unidades y semántica IEC; fail-closed para campos no cubiertos.
4. **P4V11D — benchmark de red:** uno o más casos reproducibles de red, incluyendo al menos un caso con transformador y neutro/Z0 explícitos.
5. **P4V11E — revisión IEC 60909-0:2026:** contraste específico del método/resultado 2F-T contra la edición objetivo.
6. **P4V11F — Workspace V4:** representación 2F-T en la misma UI, sin cálculo JavaScript.
7. **P4V11G — gate de madurez:** CI completo y actualización de `FAULT_SCOPE` solo después de todos los gates anteriores.

## Qué valida automáticamente el proyecto

- identidades matemáticas;
- benchmark independiente;
- consistencia de unidades;
- escenarios MAX/MIN;
- preservación de Z0/Z1/Z2;
- no aproximación 2F-T→2F/1F-T;
- regresiones P1–P5 existentes;
- representación visual estructural.

## Qué requiere revisión profesional/normativa

La evidencia pública permite confirmar que IEC 60909 contempla la categoría line-to-line with earth y que pandapower no la implementa directamente. Sin embargo, una afirmación de **verificación integral** contra IEC 60909-0:2026 requiere revisión controlada del texto completo licenciado y trazabilidad de las cláusulas/ecuaciones aplicables.

Ese gate debe quedar como revisión del ingeniero/revisor autorizado. No se sustituye por una afirmación automática del software.

## Políticas que permanecen

```text
professional_emission = false
automatic_dispatch = false
crosscheck = false
```

P5 continúa en paralelo en su propia rama; este trabajo no revierte ni invalida P4-v1 ya cerrado.
