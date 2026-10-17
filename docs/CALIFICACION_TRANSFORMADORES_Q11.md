# Q11 — Banco externo de transformadores

El banco ejecuta **OpenDSS mediante MCP stdio**. Contrasta ocho casos
publicados IEEE4 y 48 variantes controladas con referencias independientes.
Los resultados de aceptación se guardan en `Summary.json` y en los artefactos
Linux/Windows del workflow `transformer-qualification`.

## Fuentes y condiciones

Los ocho casos publicados combinan:

- 12.47/4.16 kV reductor y 12.47/24.9 kV elevador;
- estrella aterrizada–estrella aterrizada y delta–estrella aterrizada;
- cargas equilibradas y desequilibradas por fase.

Datos IEEE4: banco de 6000 kVA, R=1%, X=6%, fuente fija 12.47 kV, 60 Hz,
líneas de 2000/2500 pies con matrices R/X por fase. Las cargas originales
se conservan; excitación y capacitancia se omiten explícitamente conforme
al modelo del benchmark. El neutral de línea está reducido en la matriz.

Las tablas fueron publicadas como transcripción de IEEE por Power Grid Model
IO y están fijadas al commit `4cb5f85c7e361bd68243036ca255d2100ed0a937`.
Se verifican contra los archivos upstream completos, no solo un resultado.
Ver [procedencia y licencia de los datos](../examples/qualification/ieee4/README.md)
y [selección de tesis y casos reales](INVESTIGACION_CASOS_SUBESTACIONES.md).

## Variantes controladas y oráculo

No se atribuyen a IEEE ni a una instalación real las 48 variantes adicionales:

- 42 combinaciones: siete grupos admitidos —Yy0, Yyn0, Dd0, Dyn1, Dyn11,
  Yd1, Yd11—, tap en HV/LV y posiciones -2/0/+2 a 2.5% por paso;
- seis combinaciones de tap con pérdidas de vacío P0=6 kW e I0=0.5%.

Estas variantes usan líneas transpuestas y carga equilibrada a media demanda.
Las secundarias delta alimentan cargas delta; no se agrega un neutral ficticio.
PYPOWER 5.1.21 resuelve AC Newton a partir de los datos declarados, sin tomar
valores numéricos de OpenDSS. Es una dependencia opcional de calificación,
no una ruta operativa. El transformador se representa con tap, desfase,
impedancia serie y admitancia de excitación en su segundo devanado.

## Criterios previos de aceptación

| Banco | Magnitud | Tolerancia absoluta |
|---|---|---|
| IEEE4 | Tensión por fase, LN en estrella / LL en delta | 5 V |
| IEEE4 | Ángulo de tensión | 1 grado |
| IEEE4 | Corriente de conductor | 5 A |
| IEEE4 | Ángulo de corriente | 1.5 grados |
| IEEE4 | Base nominal LN publicada, redondeada a 3 decimales | 0.0006 kV |
| IEEE4 | Consistencia entre V físicos y pu | 0.0001 pu |
| Controlado | Tensión | 0.0002 pu |
| Controlado | Ángulo fase A | 0.01 grados |
| Controlado | Pérdidas activas/reactivas totales | 0.05 kW / kvar |

Un caso no convergido falla la prueba. No se compara una solución anterior.
La reconstrucción del primer caso después de todos los taps verifica que
no sobreviven excitación, posiciones ni matrices de otro modelo.

## Correcciones y nueva entrada pública

Se conservan las bases explícitas HV/LV de transformadores profesionales en
el registro del núcleo. Así, agregar líneas o cargas posteriormente no
descarta esos niveles nominales y no altera indebidamente los valores en pu.

`i0_percent` conserva el significado de corriente total de vacío. OpenDSS
`%IMag` representa su componente reactiva; cuando P0 e I0 están declarados:

`IMag% = sqrt(I0%^2 - (100 * P0_kW / Sn_kVA)^2)`.

Se rechazan datos incompatibles antes de modificar un proyecto. Con datos
incompletos se conserva la dependencia explícita del motor; no se declara una
caracterización completa de excitación. La derivación queda en la ficha P2.
La separación se contrasta con el modelo shunt independiente y con la
implementación nativa:
https://github.com/dss-extensions/dss_capi/blob/0.14.5/src/PDElements/Transformer.pas

Una línea puede declarar `phase_impedance` con matrices simétricas pasivas
3x3 `r_ohm_km`, `x_ohm_km`, `c_nf_km` y `source_reference`. No se permite
mezclarlas con R1/X1/C1. Esta primera versión exige frontera de flujo explícita;
no fabrica proyección de cortocircuito de secuencia positiva o cero.

Una carga monofásica estrella puede declarar `nodes: [fase, 0]` manteniendo
`bus` como nombre de barra. `kv` es la tensión nominal fase–neutral de esa
carga. Las respuestas de flujo incluyen nodos, V LN físicos y sus ángulos;
el detalle de alimentadores agrega ángulos de corriente del terminal 1.

## Reproducción

```shell
python -m pip install -e ".[dev,qualification]"
python -m pytest tests/test_transformer_external_qualification.py -q
python scripts/verify_transformers_mcp.py --output outputs/transformers --verify-upstream
```

El directorio de salida debe ser nuevo. Los artefactos contienen entradas,
resultados públicos, referencias, comparaciones, inventario de llamadas MCP,
versiones de bibliotecas, hashes de código/datos y netlist reconstruido.

## Ejecución de aceptación conservada

Primer banco completo Linux: commit `d8a72274e0e2432d81a699c081be18666757c76b`,
[ejecución CI](https://github.com/NoeCalle/MCP-Electrico/actions/runs/39070031398/job/117505549947),
126 pruebas dirigidas y 172 llamadas MCP. La [evidencia guardada](evidence/transformers_q11_linux.json)
conserva fecha, versiones, hashes y resultados de esa ejecución. Las revisiones
posteriores de documentación no cambian retroactivamente sus hashes; los
workflows de cada revisión vuelven a ejecutar Linux y Windows.

Errores máximos publicados: 0.598 V, 0.0542 grados de tensión, 0.339 A y
0.0522 grados de corriente. En variantes controladas: 0.0000500 pu,
0.00000102 grados, 0.000499 kW y 0.00627 kvar. Todos dentro de los criterios
previos. Las pequeñas diferencias incluyen redondeo de tablas y respuestas.

## Límites

No se certifican instalaciones reales ni se aprueba el diseño. Las bajas
tensiones de algunos casos IEEE son resultados del benchmark, no una
demostración de cumplimiento de calidad de suministro.

No se califican corrientes de falla, protección, regulación automática de taps,
neutrales explícitos y su potencial, conexión abierta, bancos de tres devanados,
saturación, inrush ni otros grupos. La admisión de un grupo no implica resolver
cualquier forma de puesta a tierra: el banco usa los modelos explícitos descritos.
La verificación desequilibrada se limita a estos ocho casos, no a todo alimentador
IEEE/EPRI ni al 90% de estudios avanzados.
