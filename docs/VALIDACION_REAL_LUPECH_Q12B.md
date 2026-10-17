# Q12B: soportabilidad de cables de un proyecto industrial real

Fecha: 17 de octubre de 2026.

## Fuente y alcance admitido

Cristina Lopez Rodriguez-Rosello, Comillas, 2023:
[Unit Substation Design for Petrochemical and Lube Integration Project LuPech
(J-18) at IOCL Gujarat Refinery](https://repositorio.comillas.edu/items/0e385354-9a7f-4378-887c-bf0758f09e9e).
La ficha describe el diseno ESS-044 en colaboracion con Intecsa Industrial.
Es un proyecto real de ingenieria publicado; no es evidencia de construccion,
puesta en servicio ni medicion en campo.

Se revisaron visualmente las paginas completas 158-161. La fuente tiene 575
paginas y 14.701.456 bytes; SHA256:
`9b913704951cd8d3f876a7e7dc71565e221d75fecf3b4a26ff0b35fed7213dd4`.
La numeracion PDF de esas paginas coincide con la impresa.

Se admite **el calculo adiabatico publicado de siete selecciones de cables**
de las tablas 105, 106 y 107. Hay corriente, tiempo, k, seccion y resultado
minimo explicitos. No se presenta esta admision como reproduccion completa de
flujo, cortocircuito, coordinacion o instalacion.

El PDF y las imagenes de sus paginas no se redistribuyen. El repositorio de
origen declara CC BY-NC-ND 3.0 US. Se conservan unicamente hechos numericos
atribuidos, localizadores, enlace y hash para revisar la transcripcion.

## Entradas y resultado verificable

La fuente indica aluminio XLPE, temperaturas 90/250 C y k=94 A sqrt(s)/mm2
(p.159). La corriente de 40 kA es un **criterio de diseno de cables publicado**:
este banco no la calcula con IEC 60909 ni la identifica con una barra ETAP.
Los tiempos son duraciones de soportabilidad publicadas, no tiempos
comprobados contra curvas de reles o interruptores.

La p.158 exige que cada cable individual soporte una falla en ese cable aun
cuando existan paralelos. Se conserva esa politica: ni se suma la seccion de
los tres tendidos ni se divide la corriente para convertir el resultado en PASS.

| Tabla / columna | kV | Falla kA | Tiempo s | Seccion individual mm2 | Minimo publicado mm2 | Check adiabatico |
|---|---:|---:|---:|---:|---:|---|
| 105 / entrada | 33 | 40 | 1 | 630 | 425,53 | PASS |
| 105 / salida | 33 | 40 | 1 | 300 | 425,53 | FAIL |
| 106 / entrada | 11 | 40 | 1 | 500 | 425,53 | PASS |
| 106 / salida | 11 | 40 | 1 | 500 | 425,53 | PASS |
| 107 / motor menor | 6,6 | 40 | 0,25 | 240 | 212,77 | PASS |
| 107 / motor mayor | 6,6 | 40 | 0,25 | 240 | 212,77 | PASS |
| 107 / transformador | 6,6 | 40 | 1 | 500 | 425,53 | PASS |

Las secciones minimas se contrastan con precision impresa de 0,01 mm2. El
oraculo usa Decimal de 40 digitos desde los hechos fuente, sin importar codigo
productivo ni utilizar salidas MCP como entradas. El MCP aplica su herramienta
publica `evaluar_soportabilidad_termica_conductor_p5c` al conductor individual.
Se comparan I2t, k2S2, utilizacion, corriente admisible y tiempo admisible con
tolerancia relativa 1e-12 y piso absoluto 1e-10, fijados antes de ejecutar CI.

La salida de 33 kV de 300 mm2 tiene capacidad 795.240.000 A2s frente a una
demanda de 1.600.000.000 A2s. Con esas entradas, soporta aproximadamente
0,497 s a 40 kA, frente a 1 s exigido. La discrepancia queda abierta en el
documento de diseno. Un FAIL del conductor es el **resultado esperado del
banco**, no un fallo de la prueba ni evidencia de defecto de la obra construida.

No se propone una correccion constructiva: hace falta aclarar la revision de
la tabla, el criterio por tendido y la proteccion efectivamente instalada.

## Banco MCP y regresiones

`scripts/verify_lupech_cables_mcp.py` ejecuta:

- Siete casos publicados, separados de los controles sinteticos.
- Catorce controles a 0,999 y 1,001 veces la seccion minima; deben cambiar
  entre FAIL y PASS y no se atribuyen a la tesis.
- Tres rechazos por ausencia de fuente de k, tiempo o seccion.

Son 24 llamadas MCP por plataforma. Los trabajos `real-design-cables` de
Linux y Windows comprueban tambien el PDF upstream integro contra el hash,
guardan entradas, respuestas, oraculo, diferencias, versiones y hashes de
codigo en `Summary.json`. Un cambio upstream requiere revisar la fuente,
no cambiar silenciosamente el valor esperado. No se descarga la fuente
durante pruebas unitarias ni en operacion productiva.

El informe y sus indicadores separan `comparison_passed` del PASS/FAIL del
conductor; `complete_real_project_qualified`, `field_validation`,
`short_circuit_model_validated`, `protection_clearing_times_validated` y
`full_standard_compliance_claim` siguen en false.

## Pendiente integral

Se avanza en el contraste externo numerico de P5C con datos de un proyecto
real. VP-P5C-03 permanece abierto en su alcance completo: falta relacionar
la corriente de una barra de la misma revision del modelo con un dispositivo,
su rating y su despeje trazable. Tambien siguen abiertas la calificacion
integral de la red, la revision normativa licenciada y la aprobacion del estudio.
No se cambia el cierre Q11 ni se afirma cobertura general del 90%.

## Reproduccion

```shell
python -m pip install -e ".[dev]"
python -m pytest tests/test_lupech_real_cables.py tests/test_p5c_protection_checks.py -q
python scripts/verify_lupech_cables_mcp.py --output outputs/lupech-cables --verify-upstream
```
