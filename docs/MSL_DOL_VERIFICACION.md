# Dinámica DOL con MSL — verificación del alcance

## Confiabilidad técnica y responsabilidad del ingeniero — Q3

El MCP es una herramienta de cálculo para el ingeniero. Su desarrollo debe demostrar
que las entradas se traducen correctamente, que los resultados son reproducibles
y contrastados, y que los datos faltantes, supuestos, límites y errores se informan.
El ingeniero selecciona los criterios del proyecto, revisa los resultados,
aprueba el estudio y lo firma. Esa aprobación es una responsabilidad externa;
no es un módulo numérico pendiente de implementar.

Los campos históricos `professional_emission=false` y `professional_report=false`
indican que el software no aprueba ni firma automáticamente. No prohíben el uso
profesional del cálculo ni la firma del ingeniero. Una firma digital integrada
sería una mejora documental opcional y no una condición para verificar un solver.
Los estados experimentales se conservan exclusivamente cuando falta evidencia
técnica de la integración o del alcance. Arc Flash permanece diferido.

Actualizado el 4 de octubre de 2026. Estado técnico: **VERIFIED_IN_SCOPE**,
madurez **VALIDATED_WITH_LIMITATIONS**. SCR mantiene su calificación separada.

## Alcance cerrado

El MCP configura máquinas `IM_SquirrelCage` de MSL 4.0.0 y ejecuta OpenModelica
1.27.1 con DASSL. La red es un equivalente RL equilibrado explícito referido a
la barra común. Las máquinas usan parámetros SI de devanado, resistencias
fijas, inercias declaradas, curva de carga explícita y arranque directo.
Se procesan corrientes y tensiones RMS por ciclo, par, velocidad, aceleración y
criterios del paquete, con ejecución nominal y refinada.

La verificación cuantitativa cubre una máquina estrella/delta de referencia,
variación de inercia y temperatura declarada, y casos sintéticos de una/dos
máquinas delta con red RL, carga por tabla y mecanismo antirretorno declarado.
El contrato admite hasta ocho máquinas; esa cota de admisión y presupuesto
no equivale a ocho configuraciones físicas contrastadas ni a validación de
todas las combinaciones de equipos y cargas.

## Referencia original independiente

`scripts/msl_dol_native_reference.py` **hereda la clase original**
`Modelica.Electrical.Machines.Examples.InductionMachines.IMC_DOL` de la
biblioteca instalada. No llama al constructor de modelos del MCP ni agrega
ecuaciones eléctricas o mecánicas propias.

Las especializaciones están declaradas antes del contraste: `TLoad=0`, conexión
delta/estrella, tensión, inercia, temperatura fija y resistencia de contacto
`Ron=1e-6 Ω`. El torque cuadrático nativo con `TLoad=0` equivale exactamente a
la tabla de carga cero del MCP. Esta prueba no demuestra equivalencia entre
una curva cuadrática continua y una tabla arbitraria bajo carga.

El archivo original etiqueta `VNominal` como tensión por fase, pero configura
la amplitud de fuente como `sqrt(2/3)*VNominal`. Por sus ecuaciones, `VNominal`
corresponde a tensión RMS entre líneas. El adaptador emplea explícitamente
`kv_ll`; la equivalencia se comprueba ejecutando ambos circuitos.

La lectura del CSV nativo usa cuadratura independiente de la función de resumen
operativa del MCP. Los límites se guardan **antes** de ejecutar los casos:
corriente/par/velocidad relativos ≤0,001, tiempo de aceleración absoluto
≤0,001 s y tensión absoluta ≤0,0002 pu. Son tolerancias de contraste, no
criterios normativos de diseño.

| Caso de referencia sin carga | Tensión entre líneas | Inercia externa | Temperatura de resistencias fijas | Tiempo hasta 90 % de velocidad síncrona desde el cierre |
|---|---|---|---|---|
| Delta | 100 V | 0,29 kg·m² | 293,15 K | 0,374447891 s |
| Estrella, igual tensión de devanado | 173,205 V | 0,29 kg·m² | 293,15 K | 0,374448789 s |
| Delta, doble inercia externa | 100 V | 0,58 kg·m² | 293,15 K | 0,543745783 s |
| Delta, misma resistencia declarada a otra temperatura | 100 V | 0,29 kg·m² | 353,15 K | 0,374447891 s |

Los cuatro casos aprobaron: error relativo máximo de corriente 4,324e-6,
error absoluto máximo de tensión 5,141e-6 pu y diferencias de par,
velocidad y tiempo inferiores a sus límites. Las trazas comparan los 70 ciclos
posteriores al cierre. La relación de corriente final estrella/delta se
verifica para igual tensión de devanado; no se sustituye corriente de línea
por corriente de devanado.

## Convenciones comprobadas

- R y L: valores SI por devanado del estator; rotor equivalente trifásico
  referido al estator, según el componente MSL.
- Temperatura: las resistencias ingresadas corresponden a la temperatura
  declarada y permanecen fijas; `alpha20s=alpha20r=0`. Cambiar solo la etiqueta
  de temperatura **no representa calentamiento ni corrige resistencias**.
- Inercia rotativa: `Jr + JLoad`. El estator está fijo (`useSupport=false`);
  `Js` no se suma a la inercia acelerada.
- Pérdidas: cobre con resistencias fijas. Pérdidas de núcleo, adicionales,
  fricción interna y evolución térmica están deshabilitadas en este contrato.
- Corrientes: terminales de línea, RMS por ciclo. El sensor cuasi RMS de MSL
  es una magnitud distinta durante transitorios.
- Tensión de barra y terminal: RMS entre líneas, informadas por separado.

En ambos circuitos se comprobó además `∫τ_e·ω dt = Δ[½(Jr+JLoad)ω²]` para
esta especialización sin carga/fricción. Límite relativo prefijado: 0,0001.
Error observado máximo: 1,455e-12. Esta igualdad es una comprobación de lectura,
unidades y mecánica del caso de prueba; no un nuevo solver operativo.

## Regresión con carga y bloqueo

`scripts/verify_modelica_motor_adapter_mcp.py` ejecutó nuevamente los tres casos
de una máquina cargada, dos máquinas sobre la misma red RL y rotor casi
bloqueado. Se verificaron nominal/refinado, interacción de red y diferencias
de aceleración, oráculo nodal independiente para corriente/par de rotor casi
bloqueado y rechazo del criterio mecánico cuando no acelera.

En total: **22 llamadas MCP reales, siete casos DOL del adaptador, cuatro
ejecuciones del ejemplo original y ocho balances mecánicos**. La biblioteca
y el compilador se identifican mediante versiones/hashes; no se modificaron
las fuentes MSL. Las pruebas públicas ordinarias no instalan OpenModelica:
la evidencia física local y la CI de contratos se identifican por separado.

## Condiciones de cierre resueltas

| Condición | Evidencia | Estado |
|---|---|---|
| DOL01 — ejemplo original y MCP | Cuatro variantes de `IMC_DOL`, entradas y límites previos, comparación independiente de CSV | Aprobada |
| DOL02 — fase, pérdidas, temperatura e inercia | Estrella/delta, temperatura fija, cambio de JLoad y balances mecánicos | Aprobada |
| DOL03 — regresión reproducible y límites | Siete ejecuciones por MCP, runtime fijado, refinamiento, rechazo de red fuera del equivalente | Aprobada |

## Reproducción

Configurar el runtime ya instalado mediante `configurar_dinamica_modelica`.
Ejecutar:

```text
python scripts/verify_msl_dol_qualification_mcp.py --output <carpeta-nueva>
python scripts/verify_modelica_motor_adapter_mcp.py --omc <omc> --msl <MSL-4.0.0> --output <otra-carpeta-nueva>
```

`Predeclared-plan.json`, `Evidencia-DOL-MCP.json`, comparaciones, fuentes
generadas, comandos, trazas y hashes conservan la evidencia. Los ejemplos
son casos de verificación; no constituyen fichas de las bombas del usuario.

Quedan excluidos la traducción automática de todo el unifilar, cargas de
potencia constante de fondo, saturación/temperatura variable, modelos de
fabricante y variadores. El cierre DOL no habilita SCR por inferencia: SCR tiene sus propios cierres Q4/Q5. La revisión, aprobación y firma corresponden al ingeniero.

Consultar el [registro vigente](ESTADO_CIERRE_MODULOS.md) y la
[verificación SCR](MSL_SCR_VERIFICACION.md).
