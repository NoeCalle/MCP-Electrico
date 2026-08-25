# P3C11A — Primer subconjunto primario de Tabla 5A

## Estado

**SUBCONJUNTO PRIMARIO VERIFICADO; COBERTURA DE FAMILIA P3C11 PENDIENTE.**

Este bloque inicia P3C11 con evidencia primaria de corrección por temperatura sin convertir una tabla completa en un dataset automático por haber validado unas pocas celdas.

La fuente es la copia oficial del CNE–Utilización 2006 ya pinneada por el proyecto:

```text
source_id = MINEM_CNE_UTIL_2006_OFFICIAL_PDF
sha256 = 2b3cbd457c519bf9d9aa2cf2754c72b6e531708e45ea2fdf91f839b1acccfd64
```

La Tabla 5A fue localizada reproduciblemente en:

```text
PDF 563
Tablas - Pág. 16 de 82
```

La captura se generó mediante GitHub Actions run `32897924798`, artefacto `9581927062`.

## Subconjunto efectivamente revisado

Se revisó visualmente el bloque **XLPE o EPR — cables al aire** y se fijaron únicamente:

```text
35 °C -> 0.96
40 °C -> 0.91
```

Para impedir que estas celdas se generalicen fuera del alcance literalmente visible en la Tabla 5A, el dataset se restringe además al routing inequívoco:

```text
Método A1
XLPE/EPR
3 conductores cargados
Tabla 2, columna 15
factor de temperatura -> Tabla 5A
```

La correspondencia A1/columna 15 se verificó en Tabla 3, PDF 555 / Tablas - Pág. 8 de 82.

Dataset:

`PERU_CNE_UTIL_2006_TABLE_5A_XLPE_AIR_A1_COL15_PRIMARY_V1`

El lookup utiliza `exact_rows_v1`. No interpola, no extrapola y no usa vecino más cercano. Una temperatura distinta de 35/40 °C o una consulta con otra columna/método devuelve `VALUE_NOT_TABULATED`.

## Inconsistencia normativa detectada

La copia oficial contiene una tensión interna que debe permanecer visible:

1. el primer bloque de Tabla 5A dice ser aplicable a las **columnas 2 a 16** de Tablas 1 y 2;
2. Tabla 3 remite también B1/B2/C/D a Tabla 5A, aunque las columnas XLPE/EPR de esos métodos llegan hasta 25;
3. la Nota 3 de Tabla 2 también remite a Tabla 5A para efectos de mayor temperatura ambiente;
4. el Manual de Sustentación indica usar Tabla 5A-a para conductores al aire/canalización cuando el ambiente excede 30 °C y 5A-b para ductos enterrados con temperatura distinta de 20 °C, pero esa explicación no elimina expresamente la restricción de columnas impresa en Tabla 5A.

Por ello el proyecto adopta política **fail-closed**:

- no se aplica automáticamente este dataset al caso P3C10 de método C / Tabla 2 col. 23;
- no se infiere que 0.96 o 0.91 sean utilizables en columnas 17–25 solo porque Tabla 3 remita a Tabla 5A;
- la inconsistencia debe resolverse con evidencia normativa adicional o decisión profesional documentada antes de ampliar ese alcance.

## Evidencia y revisión

La revisión queda registrada como:

```text
reviewer = GPT-5.6 Sol
human_reviewer = null
review_mode = AI_VISUAL_REVIEW_USER_AUTHORIZED
review_authorized_by_user = true
manual_comparison_confirmed = true
review_result = APPROVED
review_confidence = HIGH
```

La aprobación se limita a las celdas/routing descritos. No se presenta como revisión humana.

## Cobertura P3C11

`PRIMARY_VERIFIED` de una o varias celdas **no significa cobertura completa de una familia normativa**.

Por ello los datasets primarios puntuales declaran:

```text
p3c11_family_coverage = false
```

El gate P3 solo considera una familia 5A/5B/5C/5D/5E cerrada cuando exista una declaración explícita de cobertura para el alcance P3-v1. Esto endurece también el tratamiento del subconjunto primario actual de Tabla 5C.

P3C11 permanece `PENDING`.

## Binding hacia Iz

Este PR deliberadamente **no conecta todavía** el nuevo factor genérico a `Iz`.

Razón: antes de permitir que un factor 5A entre al cálculo, el binding debe comprobar de forma determinista al menos:

- perfil/referencia normativa;
- método de instalación;
- tabla y columna de la `Iz_base` normativa;
- aislamiento;
- ambiente;
- temperatura consultada;
- alcance exacto del dataset.

Hasta implementar ese contrato, `automatic_binding_to_iz = false`.

## Eje visual V3

V3 no debe mostrar como aplicado un factor que todavía no ha sido vinculado al cálculo. El siguiente subbloque visual, junto con el binding genérico, deberá presentar la trazabilidad del factor (`axis`, tabla, dataset, valor y condición) preparada en Python.

El navegador continúa sin resolver tablas ni recalcular ingeniería.
