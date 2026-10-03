> Documento histórico: el solucionador físico propio descrito aquí fue
> retirado el 2026-10-02. Sus herramientas no ejecutan nuevos estudios.
> Estado vigente: [migración a modelos abiertos](MIGRACION_MODELOS_ABIERTOS.md).

# P13G — Arranque suave: aproximación SCR/RL con dinámica mecánica

## Alcance de esta ampliación

Se añade un modelo **aproximado y explícito**, distinto de P13F DOL. Controla
rampa de tensión fundamental, límite de corriente RMS del equivalente, aceleración
y bypass. Un motor dinámico por estudio. No está validado contra un arrancador
real y no reproduce las conmutaciones de una red trifásica de tres hilos.

La documentación de P13F conserva su alcance DOL: esta capacidad es aditiva.
No se declara que completar ensayos sintéticos valide la estación de bombeo M1.

| Capacidad | Alcance |
|---|---|
| Rampa | Fracción de tensión **fundamental** respecto de la entrada; rampa temporal lineal explícita. No se identifica con el porcentaje de tensión RMS total de una ficha SCR sin comprobar su definición. |
| Limitación | Prioridad sobre la rampa. Busca el ángulo de disparo que deja la corriente RMS del equivalente por debajo del límite explícito en A. |
| Motor | Circuito fundamental P13F dependiente del deslizamiento y ecuación mecánica RK4. |
| Red | OpenDSS aislado de secuencia positiva, con demanda fundamental del conjunto SCR/RL. |
| Bypass | Se enclava sólo después de alcanzar tensión plena, velocidad declarada y tiempo continuo de mantenimiento. No se cierra por terminar simplemente la rampa. |
| Resultados | Velocidad, par, corriente fundamental y RMS equivalente, tensión de entrada y del motor, ángulo calculado, estado del control, energía e I²t equivalente. |
| Verificación | Tres mallas dt/dt2/dt4, balance de energía, lecturas nativas OpenDSS, replay y hashes. |

## Referencias y formulación

[Risø-R-1400, segunda edición, sección 2.2.2, página impresa 22](https://backend.orbit.dtu.dk/ws/portalfiles/portal/7703047/ris_r_1400_ed2.pdf)
describe una aproximación dqo de arranque suave de una fase con carga RL, y la
dependencia no lineal entre ángulo, amplificación y factor de potencia. Esto
motiva el equivalente; **no demuestra equivalencia con PowerFactory ni con un
modelo de fabricante**. El presente código deriva y prueba sus propias ecuaciones.

[Siemens 3RW30/3RW40, manual de aplicación](https://support.industry.siemens.com/cs/attachments/38752095/Manual_softstarter_3RW30_3RW40_en-US.pdf)
describe la prioridad de la limitación de corriente sobre la rampa. No se adoptan
valores físicos de ese producto como datos de M1.

Con `phi=arg(Z)` y `alpha>phi`, el equivalente RL pasivo tiene:

```text
i(theta)/(Vpeak/|Z|) = sin(theta-phi)
                      - sin(alpha-phi)*exp(-(theta-alpha)/tan(phi))
alpha <= theta <= beta; i(beta)=0
```

Para `alpha<=phi` se recupera conducción continua y el caso a tensión plena.
Las integrales analíticas de Fourier dan la corriente fundamental compleja y
la tensión fundamental del motor. La identidad de potencia del RL periódico
da su corriente RMS total; los tests la contrastan contra integración temporal
independiente de la ecuación RL con SciPy, incluyendo corriente, ángulo de extinción
y tensión RMS. Para carga puramente resistiva también se verifica la solución cerrada.

Se transforma el circuito de motor equilibrado a su equivalente de línea/fase
de secuencia positiva para calcular `R` y `X` al deslizamiento actual. Esta
aproximación no reproduce los intervalos de conducción de dos/tres fases de un
arrancador real conectado a un motor sin neutro, ni la cancelación exacta de armónicos.

La potencia tomada de la red incluye la componente fundamental del motor y un
término adicional del equivalente RL. Ese término se contabiliza en energía
separadamente: **no se presenta como calor real del motor ni pérdida del SCR**.
Los SCR se consideran interruptores ideales. El par se calcula únicamente con
la componente fundamental. No se integra almacenamiento magnético.

## Contratos públicos

- `obtener_contrato_arranque_suave()`.
- `validar_dinamica_arranque_suave(manifest_referencia_dol, paquete_dinamico, opciones, arrancador)`.
- `ejecutar_dinamica_arranque_suave(...)`.
- `generar_dossier_arranque_suave(..., directorio_salida)`.
- `verificar_integridad_dossier_arranque_suave(ruta_indice)`.

El manifiesto DOL es **la referencia del motor a tensión plena**, usada para
calibrar corriente de rotor bloqueado, fp y potencia nominal. No se cambia
silenciosamente el método de un manifiesto SCR ni se interpreta su corriente
limitada como corriente de rotor bloqueado DOL. Se conservan las validaciones
y SHA del paquete P13F. El resultado público identifica el método aproximado SCR.

`arrancador` exige esquema, modelo, reconocimiento del alcance, conexión,
modo de control, motor, tensión inicial fundamental, tiempo de rampa, límite
en A, velocidad y tiempo de bypass, procedencia y evidencia por estudio.
No hay ajustes físicos por defecto. Dentro de cada evaluación, 30 bisecciones
invierten la ganancia y 26 buscan el límite; se comprueba la corriente resultante.
El presupuesto total es 20000 pasos mecánicos sumando estudios y refinamientos.

## Criterios y estados

Para cada estudio se exige tipo de criterio (`ILLUSTRATIVE`, `PROJECT_REQUIREMENT`,
`MANUFACTURER_LIMIT`, `NORMATIVE_REQUIREMENT`), documento, edición, cláusula,
aplicabilidad, procedencia y magnitud de tensión `MOTOR_FUNDAMENTAL_RMS`.
No se autentica automáticamente la fuente ni se inventa un mínimo universal.

**Una rampa SCR reduce deliberadamente la tensión del motor.** No reutilizar
un mínimo DOL de 80/85/90 % como aceptación de toda la rampa. La tensión de entrada,
aceleración, duración, controles y límites de fabricante deben evaluarse en sus
puntos y estados correspondientes. La primera versión sólo compara el mínimo
fundamental del motor y el tiempo con los umbrales declarados del paquete.

- `BLOCKED_SOFT_STARTER_READINESS`: datos, alcance o evidencia insuficientes; no se resuelve.
- `SOFT_STARTER_INTEGRATION_FAILED`: fallo numérico/de red; no se emite un dossier listo.
- `SOFT_STARTER_VALIDATION_FAILED`: discrepancia entre mallas/energía/control.
- `SOFT_STARTER_STUDIES_COMPLETED`: cálculo numéricamente verificado dentro del equivalente.
- `criterion.passed`: comparación matemática separada con los valores declarados.
- `design_acceptance_status=NOT_DEMONSTRATED` y `professional_emission=false` permanecen explícitos.

Un motor que queda bloqueado por corriente insuficiente puede tener un cálculo
válido y criterios incumplidos. No se transforma ese resultado en error del MCP.

## Pruebas y siguiente ampliación

El [contraste estructural trifásico](P13G_REFERENCE_COMPARISON.md) añade la
herramienta `contrastar_arranque_suave`. Su referencia resistiva en estrella
sin neutro revela diferencias del equivalente por fase incluso a igual
tensión fundamental. Este diagnóstico no valida un motor, fabricante o
aceleración SCR; conserva la madurez aproximada y la aceptación de diseño
pendiente.

El [contraste externo con motor Modelica](P13G_MODELICA_REFERENCE.md) ya está
ejecutado en un caso sintético con entradas reproducidas, y añade la herramienta
`contrastar_dinamica_con_modelica`. Las discrepancias de corriente, par y tiempo
mantienen el equivalente sin cualificación. Este benchmark no sustituye la
validación del controlador real, la red conjunta ni los motores M1/M2.

`tests/test_p13g_soft_starting.py` comprueba RL numérico independiente, referencia
resistiva, inversión del control, recuperación exacta de DOL, rampa, límite,
bypass, bloqueo, no convergencia, mallas insuficientes, procedencia, aislamiento,
replay, portabilidad y detección de expedientes alterados.

Ejemplo **sintético, no M1**: combinar los tres archivos `p13_dynamic_rms_*.json`
con `examples/p13_soft_starter_controller.json`. El mínimo de tensión heredado
del fixture DOL está marcado ilustrativo y puede incumplirse durante la rampa;
no se modifica para forzar un PASS.

Pendientes para una representación de dispositivo: caracterización/benchmark
trifásico de SCR conectado al motor real, armónicos y pérdidas/limitaciones térmicas
del equipo, lógicas y parámetros definidos por fabricante. Dinámica simultánea
de varios motores y VFD requieren extensiones separadas. Arc Flash sigue diferido.
