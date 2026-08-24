# P2 — Datos profesionales v1

## Estado

**P2 está EN IMPLEMENTACIÓN.** Esta entrega cubre el primer corte vertical: transformadores trifásicos de dos devanados, red equivalente positiva-secuencia, QA dependiente del estudio, proyección OpenDSS/pandapower y acompañamiento visual V2.

No cierra todavía P2 completo. Permanecen pendientes la separación formal `CableType/CableInstallation`, R0/X0 o geometrías suficientes, pantallas/bonding MT avanzados y mayor cobertura de equipos/conexiones.

## Principio

Un parámetro ausente no se convierte en un valor típico. El modelo distingue:

- dato explícito;
- valor derivado mediante fórmula documentada;
- dato `NOT_AVAILABLE`;
- supuesto de proyección impuesto por el comportamiento del solver.

Los supuestos de proyección nunca se presentan como datos profesionales.

## Transformador profesional

Tool: `agregar_transformador_profesional(...)`.

Datos principales:

- kVA;
- kV HV/LV;
- `uk_percent`;
- grupo vectorial;
- X/R o pérdidas de carga;
- pérdidas en vacío e I0 cuando existan;
- taps;
- fabricante/modelo opcionales;
- referencia/URL de procedencia.

### Separación R/X

Si existe X/R:

`R% = uk% / sqrt(1 + (X/R)^2)`

`X% = R% · X/R`

Si existen pérdidas de carga:

`R% = Pcu_kW / Snom_kVA · 100`

`X% = sqrt(uk%^2 - R%^2)`

Si X/R y pérdidas de carga se suministran simultáneamente y resultan incompatibles en más de 10 %, la operación falla. No se elige uno de los datos silenciosamente.

### OpenDSS

La proyección usa `%Rs` por devanado y `XHL`. Para un transformador de dos devanados, el R total derivado se reparte en dos mitades iguales mientras no exista un reparto explícito por devanado.

Si `no_load_loss_kw` o `i0_percent` faltan, no se inventan. OpenDSS conserva su comportamiento por defecto y el registro marca la proyección como incompleta con un supuesto visible. Esa condición debe revisarse antes de usar el modelo para una finalidad que dependa de esas magnitudes.

### pandapower

Pandapower exige `pfe_kw` e `i0_percent` para `create_transformer_from_parameters`. Por ello un transformador P2 sin esos datos devuelve `PP012`; no se sustituyen por cero.

La madurez del flujo pandapower continúa `EXPERIMENTAL`.

## Grupos vectoriales P2 v1

La primera cobertura se limita a combinaciones que podemos traducir explícitamente sin aproximar:

- Dd0;
- Yy0 / Yyn0;
- Dyn1;
- Dyn11;
- Yd1;
- Yd11.

El reloj 1 se representa como LV atrasada 30° y el 11 como LV adelantada 30°. Grupos fuera de esta cobertura se rechazan.

## Red equivalente aguas arriba

Tool: `definir_red_equivalente(...)`.

Registra:

- tensión LL;
- Scc3 máxima + X/R;
- Scc3 mínima + X/R opcionales;
- escenario activo;
- procedencia.

Para el escenario activo se deriva:

`|Z1| = kV_LL^2 / Scc3_MVA`

`R1 = |Z1| / sqrt(1 + (X/R)^2)`

`X1 = R1 · X/R`

OpenDSS recibe `MVAsc3` y `X1R1` del escenario activo.

## Secuencia cero

Scc3 y X/R positiva no determinan Z0. Por eso esta entrega declara:

`zero_sequence.status = NOT_AVAILABLE`

No se deriva `MVAsc1`, R0 ni X0. El QA convierte esa carencia en bloqueante cuando el estudio solicitado necesita fallas a tierra/secuencia cero.

## QA dependiente del estudio

Un transformador legado sin ficha P2 puede ser una advertencia para un flujo ya validado dentro de su alcance, pero se vuelve bloqueante cuando se solicita un estudio de falla que necesita los datos profesionales ausentes.

De la misma forma, una fuente ideal puede ser suficiente para un flujo exploratorio, pero no se presenta como red equivalente profesional para cortocircuito.

## Workspace V2

El snapshot sube a `schema_version = 2` e incluye:

- `model.source`;
- `transformer.professional`;
- `line.conductor_assignment`;
- bloque superior `professional`.

El inspector muestra para transformadores P2 grupo vectorial, uk/%Z, X/R, pérdidas, taps, procedencia y estado de secuencia cero. En `sourcebus` muestra Scc3 máxima/mínima, X/R, escenario activo y procedencia.

El navegador continúa siendo read-only: no deriva impedancias ni ejecuta estudios.

## Fuera de alcance de esta entrega

- Iz normativo / P3;
- IEC 60909 / P4;
- TCC / P5;
- IEEE 1584 / P6;
- cross-check OpenDSS/pandapower;
- selección automática de motor.
