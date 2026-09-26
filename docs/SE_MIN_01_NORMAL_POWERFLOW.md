# SE-MIN-01 — primer flujo de carga NORMAL

## Propósito

Este caso lleva al MCP Eléctrico el diseño que se viene desarrollando para una
planta concentradora de cobre en el sur del Perú.

No es un fixture genérico. Es un **caso de ingeniería del proyecto SE-MIN-01**,
todavía preliminar y con fronteras explícitas.

## Datos de diseño ya acordados

- operación 24/7;
- altitud: 3,800 m s.n.m.;
- suministro: 22.9 kV, 3 fases, 60 Hz;
- distribución principal: 4.16 kV;
- auxiliares: 480 V;
- dos barras A/B de 4.16 kV con tie normalmente abierto;
- dos barras A/B de 480 V con tie normalmente abierto;
- filosofía N-1 funcional, no producción 100 %;
- TR-01 / TR-02: 2 × 6.3 MVA, 22.9/4.16 kV;
- TR-AUX-A / TR-AUX-B: 2 × 1.5 MVA, 4.16/0.48 kV.

### Escenario NORMAL

El Load List reproducido por el manifiesto suma:

```text
P = 6.433704 MW
Q = 1.679052 MVAr
S = 6.649193 MVA
```

Cargas 4.16 kV A:

- 100-CR-101: 536.842 kW / 275.032 kvar
- 200-ML-201: 1434.949 kW / 291.379 kvar
- 200-P-201A: 860.969 kW / 174.827 kvar

Cargas 4.16 kV B:

- 300-BL-301A: 456.498 kW / 92.696 kvar
- 500-P-501A: 1020.408 kW / 207.203 kvar
- 600-P-601A: 813.138 kW / 165.115 kvar

Auxiliares 480 V:

- Barra A NORMAL agregada: 597.3 kW / 234.3 kvar
- Barra B NORMAL agregada: 713.6 kW / 238.5 kvar

Los standby no se suman automáticamente; cuando corresponda sustituyen al duty.

## Datos todavía no congelados

El MCP **no debe presentarlos como datos reales del proyecto**:

- Scc/XR de la utility;
- longitudes, secciones y R/X de alimentadores;
- grupo vectorial, grounding, %Z, X/R, taps y pérdidas finales de TR-AUX;
- taps/pérdidas finales de TR-01/TR-02.

Por esa razón este primer caso usa placeholders explícitos:

### Fuente rígida de modelado

```text
Scc = 1,000,000 MVA
X/R = 10
```

No representa el nivel de cortocircuito de la utility. Su único propósito es
eliminar prácticamente la caída aguas arriba y estudiar la arquitectura interna
sin heredar la impedancia por defecto de OpenDSS.

### Enlaces de alimentador

Los `Line.*_MODEL_LINK` tienen impedancia numérica casi nula
(`R1=X1=1e-6 ohm/km`). La longitud de 1 km es solo un valor de serialización:
**no representa una longitud física**.

Por tanto este caso **no ejecuta VOLTAGE_DROP** y no debe utilizarse para emitir
una conclusión sobre caída de tensión de cables.

### Transformadores auxiliares

Solo 1.5 MVA y 4.16/0.48 kV son datos de diseño. Para permitir este primer
flujo se usan temporalmente:

```text
Dyn11
uk = 6 %
X/R = 8
```

marcados como `MODEL_PLACEHOLDER`.

## Qué sí puede concluir este estudio

Puede revisar de forma preliminar:

- reparto P/Q entre barras A y B;
- cargabilidad aparente de la arquitectura de transformación;
- efecto de la impedancia preliminar de TR-01/TR-02;
- efecto del placeholder declarado de TR-AUX-A/B;
- tensiones en barras bajo el escenario NORMAL;
- pérdidas del modelo explícito utilizado.

No puede todavía concluir:

- caída de tensión real en alimentadores;
- ampacidad;
- cortocircuito;
- coordinación de protecciones;
- operación N-1;
- arranque de motores;
- conformidad profesional final.

## Ejecución

```text
python examples/run_operational_powerflow_reference.py \
  --manifest examples/se_min_01_normal_powerflow.json \
  --output artifacts/se_min_01_normal_powerflow_result.json
```

CI ejecuta el mismo caso en Linux/Python 3.11 y Windows/Python 3.12.

```text
automatic_defaults = false
automatic_dispatch = false
crosscheck = false
professional_emission = false
```
