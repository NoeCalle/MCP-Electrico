# P5D — Tiempo final de despeje

## Estado

**P5D IMPLEMENTADO EN ESTA RAMA — EXPERIMENTAL.**

P5D no crea una nueva curva. Consume únicamente la evaluación numérica P5B del dispositivo y decide si la semántica publicada puede promoverse a tiempo final de despeje.

```text
P5A  DONE
P5B  DONE
P5C  DONE
P5D  DONE / EXPERIMENTAL
P5E  NEXT
professional_emission = false
```

## Regla principal

Solo:

```text
TOTAL_CLEARING_TIME
```

puede convertirse automáticamente en:

```text
CLEARING_TIME_READY
```

Las semánticas:

```text
TRIP_TIME
MELTING_TIME
OPERATING_TIME
```

pueden seguir evaluándose como datos de curva P5B, pero P5D devuelve:

```text
TIME_SEMANTICS_NOT_CLEARING_READY
clearing_time = None
```

No se renombra ni interpreta una semántica por parecido.

## Banda de tiempo

Si la TCC es `SINGLE`:

```text
time_s = valor evaluado
conservative_time_s = time_s
```

Si la TCC es `BAND`:

```text
time_min_s = límite inferior
time_max_s = límite superior
conservative_time_s = time_max_s
```

La banda nunca se promedia. `conservative_time_s` es un campo auxiliar explícito para checks que necesiten un único tiempo conservador, por ejemplo el chequeo térmico P5C.

## Dominio

P5D hereda las políticas P5B:

```text
extrapolation = false
cross_segment_interpolation = false
```

Si la corriente queda fuera del segmento publicado:

```text
status = CLEARING_TIME_NOT_READY
reason = TCC_OUT_OF_DOMAIN
clearing_time = None
```

## Trazabilidad

Todo clearing time conserva:

- `device_id`;
- elemento protegido;
- corriente evaluada;
- `dataset_id`;
- `curve_id`;
- `segment_id`;
- `time_semantics`;
- fuente del dataset;
- método/bracket de interpolación cuando aplica.

## Separación de P4

Regla permanente:

```text
p4_tk_s_consumed = false
```

El `tk_s` usado por P4 para `Ith` no se convierte en tiempo de despeje.

## Herramientas públicas

- `obtener_contrato_tiempo_despeje_p5d`;
- `evaluar_tiempo_despeje_p5d`.

P5D no expone coordinación ni selectividad.

## Madurez

```text
validation_status.protection_clearing_time = EXPERIMENTAL
validation_status.protection_coordination  = NOT_IMPLEMENTED
professional_emission                      = false
```

El siguiente gate es P5E: coordinación temporal entre un dispositivo downstream y uno upstream, usando tiempos P5D trazables y comparación conservadora de bandas.
