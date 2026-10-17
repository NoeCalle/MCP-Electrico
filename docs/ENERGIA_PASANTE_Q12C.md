# Q12C: energia pasante total del interruptor y soportabilidad del conductor

Fecha: 17 de octubre de 2026.

## Problema y nueva herramienta

P5C conservaba el chequeo adiabatico con corriente y duracion explicitas.
Un interruptor limitador puede publicar directamente su integral total de
corriente, I2t. Esa energia no requiere inventar un tiempo de despeje mediante
`I2t / Iprospectiva^2`: ese cociente no describe la duracion real de su onda
limitada ni constituye una curva de despeje.

La nueva herramienta publica `evaluar_energia_pasante_conductor_p5c` comprueba
la energia total publicada frente a k2S2, junto con la capacidad de corte Icu
o el poder de corte declarado de un fusible. Conserva la ruta anterior sin
cambiar su contrato, criterios o evidencia Q12B.

Solo acepta un punto explicito con `manufacturer`, `model`, `current_ka`,
`voltage_kv`, `value`, `unit`, `semantics` y `source_reference`. Las unidades
admitidas son `A2s` y `kA2s`; esta ultima se multiplica por 1.000.000 y se
conserva la conversion en el resultado. No acepta julios como si fueran A2s.

El punto debe declarar `TOTAL_LET_THROUGH_I2T`. No se promueven integrales de
prearco o fusion. Se exige coincidencia de fabricante/modelo, elemento
protegido, tension del rating de corte y condiciones de corriente/tension del
punto. No se interpola ni extrapola una curva desde un unico dato, tampoco
hacia corrientes menores. Una seccion distinta de la asignacion P2 se bloquea.
No se consume `tk_s` de P4 ni se obtiene un tiempo TCC desde la energia.

Los datos y su aplicabilidad a la configuracion real del producto deben ser
revisados por el ingeniero; el software comprueba las identidades declaradas,
no autentica por si solo las fichas aportadas por quien lo invoca.

## Referencia primaria y resultado esperado

[ABB SACE, Electrical Installation Handbook, 2006](https://library.e.abb.com/public/561a28a17753c444c125714f00360967/1SDC010001D0204.pdf),
apartado 2.4, pagina impresa 74 / pagina PDF 77. Se inspecciono la pagina
completa renderizada. Es un ejemplo de fabricante; no una instalacion de
campo identificada ni el proyecto LuPech.

El PDF tiene 270 paginas y 1.642.486 bytes. SHA256:
`88267fa9f77cc6dfdf7d6d1581a65040ae479aba91b977afb36475ab2df89e24`.
Solo se transcriben hechos numericos atribuidos, no el PDF ni sus imagenes.

| Dato publicado | Valor |
|---|---:|
| Tension / falla prospectiva al inicio del cable | 400 V / 30 kA |
| Interruptor | ABB T1N160 In160 |
| Capacidad de corte a 400 V | 36 kA |
| Energia pasante a 30 kA | 0,75 (kA)2s = 750.000 A2s |
| Cable Cu/PVC | 50 mm2 |
| k explicito de la ecuacion publicada | 115 A sqrt(s)/mm2 |
| Capacidad exacta k2S2 | 33.062.500 A2s |
| Capacidad redondeada por ABB | 33,1 (kA)2s |

El resultado esperado es PASS de capacidad de corte (margen 6 kA) y PASS
termico. La utilizacion es aproximadamente 2,27%. Esto reproduce el chequeo
publicado al inicio del cable. La seccion minima termica no selecciona por
si sola el cable: ampacidad y caida de tension no se califican aqui.

La falla prospectiva se toma de la referencia; no se ha resuelto una fuente
Thevenin, una red completa o un flujo previo. Tampoco se recalcula la falla
minima al extremo del cable. No hay afirmacion de selectividad o backup.

## Banco de aceptacion

El script `verify_total_let_through_mcp.py` usa una sesion MCP stdio. Crea un
contenedor de registro P5 con una barra de 400 V, sin resolverlo y sin crear
cables con reactancias supuestas. El interruptor se vincula a esa barra de
referencia; el conductor de 50 mm2 conserva procedencia externa explicita.
La frecuencia del contenedor no interviene en el chequeo algebraico.

El oraculo Decimal independiente comprueba conversion de unidades, energia,
capacidad, utilizacion y seccion minima. Las tolerancias son relativas 1e-12,
con piso absoluto 1e-10. La concordancia con el valor publicado redondeado se
revisa a su precision de 0,1 (kA)2s.

Ademas del ejemplo publicado se ejecutan una conversion equivalente de
unidades y dos controles sinteticos de seccion cercanos al limite. Se
comprueban bloqueos por prearco, unidad, corriente, tension y modelo
incompatibles, y se repite el caso base al terminar. P5D debe seguir sin
tiempo de despeje al no disponer de TCC: un PASS energetico no inventa esa
curva. Las pruebas unitarias cubren tambien procedencia, capacidades de corte
insuficientes, vinculacion del conductor y valores no finitos.

Los trabajos CI `total-let-through` de Linux y Windows verifican el PDF
upstream por hash y conservan respuestas MCP, referencias, errores, versiones
y hashes de codigo en sus artefactos. No hay descarga externa en el uso
productivo de la herramienta.

## Evidencia conservada

Primera aceptacion: commit `361aa1a5c77383f039e68a41795806eea16e62f8`,
[banco Linux/Windows](https://github.com/NoeCalle/MCP-Electrico/actions/runs/39075632964).
Aprobo 47 pruebas dirigidas y 13 llamadas MCP por plataforma. Ambos verificaron
el PDF upstream y las 169 herramientas registradas. La suite general de esa
revision aprobo 1.300 pruebas, con 62 omitidas.

La [evidencia Linux](evidence/total_i2t_q12c_linux.json) corresponde exactamente
a esa revision. El refuerzo posterior de normalizacion de nombres del elemento
y su prueba de no elusion se verifican de nuevo en CI antes de integrar.
Los resultados preservan `clearing_time=null` y el bloqueo P5D sin TCC.

## Investigacion de proyectos y limite de cierre

Se reviso si LuPech publicaba curvas y tiempos finales suficientes: el
expediente no aporta el paquete necesario para vincular el criterio de
40 kA de Q12B a un despeje comprobado por curvas. No se renombra su tabla
de energia como una curva autentificada del fabricante.

Tambien se obtuvo la [tesis UNAB de Karina Blanco Usuga (2022)](https://repository.unab.edu.co/bitstream/20.500.12749/17620/1/2022_Tesis_Karina_Blanco_Usuga.pdf), anexo de la
Urbanizacion El Carmen. Contiene cifras de falla, Icu y duracion, pero no
el paquete suficiente de identidad y TCC para cerrar por inferencia la cadena.
El ejemplo ABB evita completar ese faltante con un tiempo supuesto.

Q12C amplia la validacion externa del subcalculo de proteccion/conductor
con una referencia primaria y una ruta energetica explicita. VP-P5C-03
permanece abierto para el estudio real integral y los tiempos de despeje.
El registro de madurez Q11 no se promociona por esta ampliacion. La red real
completa y la validacion de campo permanecen pendientes.

## Reproduccion

```shell
python -m pip install -e ".[dev]"
python -m pytest tests/test_total_let_through.py tests/test_p5c_protection_checks.py tests/test_p5d_clearing_time.py -q
python scripts/verify_total_let_through_mcp.py --output outputs/total-i2t --verify-upstream
```
