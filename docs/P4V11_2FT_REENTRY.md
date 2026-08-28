# P4-v1.1 — reingreso controlado de 2F-T

## Estado

**P4-v1.1 2F-T = `USABLE_WITH_DECLARED_SCOPE` para uso técnico interno.**

P4-v1 cerró 2F-T como `OUT_OF_SCOPE_P4_V1` porque pandapower 3.5.4 no ofrece una API directa para falla bifásica a tierra. Ese cierre histórico permanece correcto y no se reescribe. P4-v1.1 agrega una **extensión operacional MCP** mediante la segunda condición prevista en P4C08: solver dedicado de componentes simétricas, integración trazable con Z1/Z0 del modelo y representación V4.

La extensión puede utilizarse para modelado y estudios internos dentro del alcance declarado. La validación normativa integral y el contraste externo permanecen registrados como deuda y bloquean cualquier afirmación de conformidad integral o emisión profesional.

## Estado de uso

```text
mathematical_foundation = USABLE_WITH_DECLARED_SCOPE
model_integration       = DONE_P4V11B
operational_contract    = DONE_P4V11C
internal_network_case   = DONE_P4V11D
normative_verification  = PENDING_LICENSED_IEC_REVIEW
external_reference_case = PENDING_EXTERNAL_REFERENCE_CASE
workspace_v4            = DONE_P4V11F
operational_gate        = USABLE_WITH_DECLARED_SCOPE
professional_emission   = false
```

## Arquitectura numérica

Pandapower sigue siendo el backend para construir la red y obtener impedancias Thevenin de secuencia dentro del alcance P4. **No calcula la falla 2F-T**.

```text
modelo P2/P4
   ↓
pandapower 3.5.4
   ↓
Z1 = Rk + jXk
Z0 = Rk0 + jXk0
   ↓
Z2 = Z1   [solo alcance simétrico pasivo]
   ↓
solver MCP 2F-T de componentes simétricas
   ↓
Ia, Ib, Ic, I0, I1, I2
```

Para extraer `Rk/Xk/Rk0/Xk0`, el adaptador utiliza la ruta `1ph` de pandapower porque es la ruta soportada que construye las redes positiva y cero y expone ambas impedancias en `res_bus_sc`. **La corriente 1F-T calculada por pandapower se descarta y nunca se reutiliza como corriente 2F-T.**

No existe ni se simula:

```text
pandapower fault="2ph_ground"
```

## P4V11A — fundamento matemático

**DONE.** Alcance:

- falla franca b-c-tierra;
- `Zf = 0`;
- componentes simétricas;
- `Z2 = Z1` únicamente para red simétrica pasiva;
- `Z0` explícita;
- fuente positiva `E1` explícita;
- impedancias Thevenin pasivas con `R >= 0`, `X >= 0` y magnitud no nula;
- sin generadores, motores, convertidores ni modelos asimétricos.

Con falla franca 2F-T:

```text
Z1 + (Z2 || Z0)
```

El solver calcula `I0`, `I1`, `I2`, reconstruye `Ia`, `Ib`, `Ic` y las tensiones de secuencia/fase.

Condiciones de frontera verificadas:

```text
Ia = 0
Vb = 0
Vc = 0
I0 + I1 + I2 = 0
V0 = V1 = V2    en el nodo de falla bolted
Ia + Ib + Ic = 3 I0
```

## P4V11B — integración con el modelo

**DONE.** `mcp_electrico.iec60909_two_phase_ground`:

- toma el mismo snapshot P2/P4 vigente;
- aplica Scc/X-R MAX o MIN de la fuente;
- proyecta Z0 de fuente, líneas y transformadores con las mismas reglas P4C07;
- conserva `endtemp_degree` explícita por línea para MIN;
- obtiene `Rk/Xk/Rk0/Xk0` de la barra objetivo;
- calcula `E1 = c·Un/√3` con el mismo factor de tensión usado por P4;
- entrega Z1/Z0 al solver MCP auditado;
- no consume la corriente `1ph` del backend.

## P4V11C — contrato operacional de resultados

**DONE para uso operacional; validación normativa contractual diferida.**

Se expone:

- `Ib`, `Ic` de las fases en falla;
- corriente de retorno a tierra;
- `I0`, `I1`, `I2`;
- `Rk/Xk/Rk0/Xk0`;
- `results.ikss_ka` como **campo operativo** igual a `max_faulted_phase_rms_current` para que las capas existentes puedan visualizar/comparar una magnitud de falla.

Pero el payload declara siempre:

```text
ikss_contractual = false
skss_contractual = false
ip_ith            = false
operational_current_semantics = max_faulted_phase_rms_current
```

Por tanto, `results.ikss_ka` **no debe citarse todavía como Ik'' contractual IEC 60909 para 2F-T**. `Sk''`, `ip` e `Ith` permanecen `None`.

## P4V11D — benchmark interno de red

**DONE para el gate interno.** La regresión incluye:

- fuente equivalente con escenarios MAX/MIN y Z0 explícita;
- alimentador con R1/X1 y R0/X0/C0;
- bloqueo MIN cuando falta temperatura final explícita;
- transformador Dyn11 con ficha P2 y Z0 explícita;
- comparación neutro sólido vs neutro con impedancia;
- requisito físico de que introducir impedancia de neutro reduzca la contribución 2F-T dentro del caso reproducible.

Este benchmark interno **no sustituye** `VP-2FT-02`, que exige una referencia externa independiente.

## P4V11E — revisión IEC 60909-0:2026

**PENDIENTE DIFERIDO.** Requiere acceso controlado al texto completo licenciado y trazabilidad cláusula/ecuación/implementación. Mientras no exista esa evidencia:

```text
normative_verification = PENDING_LICENSED_IEC_REVIEW
full_conformance_claim = false
professional_emission  = false
```

## P4V11F — Workspace V4

**DONE.** La misma vista de cortocircuito admite `iec60909_2ph_ground`:

- muestra MAX/MIN preparados por Python/MCP;
- etiqueta la corriente como corriente de fase operacional, no como Ik'' contractual;
- muestra Z1/Z0 y políticas de secuencia;
- conserva los IDs de validaciones pendientes;
- no ejecuta interpolaciones, impedancias ni cálculo de falla en JavaScript;
- no crea una segunda interfaz visual.

## P4V11G — gate operacional

**`USABLE_WITH_DECLARED_SCOPE`.** Este gate no sustituye la madurez histórica `P4 = READY_WITH_LIMITATIONS` ni convierte la extensión en `VALIDATED_WITH_LIMITATIONS`.

Para uso interno se permite 2F-T cuando:

- existe modelo P2/P4 apto;
- Z0 requerida está explícita y proyectable;
- MIN tiene temperaturas finales explícitas cuando hay líneas;
- el caso pertenece a red simétrica pasiva;
- se acepta expresamente que la semántica contractual IEC y el caso externo siguen pendientes.

## Validaciones pendientes — no perder

Fuente central: `docs/VALIDACIONES_PENDIENTES.md`.

- `VP-IEC-01` — IEC 60909-0:2026 completa/licenciada;
- `VP-2FT-01` — semántica normativa exacta de 2F-T;
- `VP-2FT-02` — caso externo independiente;
- `VP-2FT-03` — revisión profesional antes de emisión.

Estas validaciones no invalidan el cálculo matemático/operacional dentro de su alcance, pero impiden elevar su afirmación de conformidad.

## Políticas que permanecen

```text
professional_emission = false
automatic_dispatch = false
crosscheck = false
```

P5 continúa como fase principal activa. Este trabajo no revierte ni invalida P4-v1 ya cerrado.
