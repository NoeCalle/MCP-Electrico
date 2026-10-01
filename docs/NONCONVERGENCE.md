# No convergencia y cargabilidad

Un cálculo no convergido no es una medición de sobrecarga. Puede haber una
limitación numérica, datos incompatibles o un problema de representación. No
se determina una causa automáticamente.

`ejecutar_flujo_potencia` conserva las claves existentes, pero cuando falla el
solver devuelve `voltajes_por_bus={}` y pérdidas `null`, junto con
`resultados_validos=false`, `estado_resultado=NO_CONVERGIO` y
`evaluacion_sobrecarga=NO_EVALUABLE`. No publica el último intento como resultado.
Los estudios de flujo y caída no leen sus corrientes ni clasifican límites.
El workspace marca esos estudios como inválidos incluso en la revisión actual.
Los clientes deben admitir pérdidas nulas. La respuesta convergida añade
`resultados_validos=true` y `estado_resultado=CONVERGIO`; esa validez numérica
no certifica los datos de entrada ni acredita cumplimiento normativo.

Para afirmar sobrecarga calculada, se necesita una solución aceptada y comparar
la corriente o potencia aparente con la capacidad aplicable del equipo. Para
transformadores se debe aclarar si se compara potencia o corriente; a tensión
distinta de nominal esos porcentajes pueden diferir. Una capacidad supuesta
solo permite una conclusión condicionada a ese supuesto.

Un balance elemental también puede detectar una consigna incompatible: si un
generador entrega 400 MW y su único camino es un transformador de 200 MVA, en
ese terminal S >= |P| = 400 MVA, al menos el 200 % de potencia nominal. Es una
cota condicionada a entregar esa potencia, no una cargabilidad obtenida de un
flujo fallido ni una prueba de inexistencia de solución eléctrica.

La calificación exige casos de referencia, residuales, balances y controles
de límites en el alcance estudiado. El número de pruebas de software no
sustituye la validación del modelo físico. Pandapower sigue siendo explícito
y experimental; no se introduce selección automática de motor ni se amplía
la calificación a redes de transmisión PV o a emisión profesional.
