# P13G — Contraste estructural con referencia trifásica

## Resultado y alcance

Se incorpora `contrastar_arranque_suave(paquete_comparacion)` como herramienta
MCP de diagnóstico, sin modificar las ecuaciones del cálculo SCR existente.
La referencia es una carga **resistiva trifásica equilibrada en estrella sin
neutro**, con seis tiristores ideales, fuente sinusoidal ideal y disparos
pareados. No es un motor ni un modelo de fabricante.

El contraste encuentra diferencias del equivalente por fase, tanto a igual
ángulo de disparo como a igual magnitud de tensión fundamental. La segunda
comparación evita atribuir toda la diferencia a una definición distinta de la
rampa. El estado del SCR permanece `ANALYTICAL_SURROGATE_NOT_DEVICE_VALIDATED`.

La discrepancia de modelo se informa separada de una falla numérica. La
referencia debe superar primero su verificación interna independiente:
cuadratura de los tramos de onda frente a las expresiones RMS publicadas.

## Referencia primaria

Dr. Ayman Yousef, *Three-phase full-wave AC voltage controllers*, repositorio
docente de la Facultad de Ingeniería de Benha University. Consultado el
2026-10-02. [PDF público](https://feng.stafpu.bu.edu.eg/Electrical%20Engineering/4981/crs-15889/Files/Ch4%20%203-phase%20full-Wave%20AC%20voltage%20controllers.pdf).
Páginas PDF 3, 20, 21 y 22, numeradas desde 1. Documento público sin fecha de
edición explícita; SHA-256 del ejemplar consultado:
`772950c31f289b38e7af45d808c0f7389899e71c3998bd4b1b5d55446a517996`.

La fuente aporta topología, tramos de onda y expresiones RMS para los tres
intervalos de conducción. Los coeficientes fundamentales se obtienen en este
proyecto integrando esos tramos; no se presentan como valores publicados por
el autor. El informe conserva procedencia y alcance.

## Magnitudes comparadas

- RMS total de tensión de fase de la carga y corriente de línea normalizadas
  respecto a conducción plena. Son iguales numéricamente en esta carga R.
- Magnitud y componente en cuadratura de la fundamental.
- Mismo ángulo: revela la diferencia topológica en la relación ángulo/salida.
- Misma magnitud fundamental: invierte cada modelo por separado y compara
  corriente RMS y cuadratura, conservando la diferencia de ángulo.

La tolerancia de comparación es explícita e **ilustrativa**; se expresa en pu
de la base de conducción plena, no como porcentaje relativo del punto. El
error relativo es otro campo. Una referencia con salida cero no produce
división por cero: el error relativo se devuelve como `None`.

## Resultado reproducible del paquete de ejemplo

Con tensión fundamental objetivo 0.4 pu:

| Magnitud | Equivalente por fase | Referencia trifásica |
|---|---|---|
| Ángulo de disparo | 110.149° | 94.748° |
| Corriente RMS normalizada | 0.533972 | 0.486649 |
| Diferencia relativa de corriente | +9.724 % | base de comparación |

Este error corresponde al **benchmark resistivo**. No se extrapola como un
error demostrado de M1, de la tensión de la estación o de su aceleración.
La tolerancia ilustrativa de 0.02 pu se incumple en varios puntos. No se
cambia para forzar acuerdo ni se interpreta como mínimo normativo.

## Verificación

`tests/test_p13g_reference.py` comprueba tramos/formas RMS, conservación de
corriente entre fases, potencia resistiva, coeficientes de Fourier, continuidad
entre modos, extremos, aislamiento de entradas/contexto, desacuerdo explícito y
rechazo de datos/tolerancias inválidos. El oráculo trifásico no utiliza el
equivalente por fase para construir su respuesta.

`scripts/verify_soft_starter_reference_mcp.py` llama el servidor mediante un
cliente MCP real, compara 37 ángulos y 5 objetivos fundamentales, repite la
consulta y comprueba que una tolerancia etiquetada como normativa se bloquee.
Guarda entradas, resultados, contrato, inventario y hashes del código/evidencia.

## Trabajo restante

El primer contraste estructural queda implementado. Para representar un
arrancador industrial aún se requiere una referencia trifásica **inductiva con
motor**, comprobar par/control/aceleración/red/bypass y obtener un caso externo
o datos de fabricante adecuados. El modelo publicado de
[Juan Sagarduy en MathWorks](https://www.mathworks.com/matlabcentral/fileexchange/49605-soft-starter-induction-motor-model)
es un candidato; requiere MATLAB/Simulink/Simscape Electrical y no se ha ejecutado
en este trabajo. No se afirma equivalencia con ese modelo.

La dinámica simultánea de varios motores continúa como ampliación separada.
Arc Flash IEEE 1584 permanece diferido.
