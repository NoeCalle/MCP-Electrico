from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"P3C10C finalize refused: {path} anchor count={text.count(old)}")
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "docs/ROADMAP_PROFESIONAL.md",
    "- `P3C10` — estrategia validada de `Iz_base`;\n",
    "- `P3C10` — estrategia validada de `Iz_base`; infraestructura P3C10A/B implementada y primer candidato Tabla 2 P3C10C pendiente de revisión humana;\n",
)

replace_once(
    "docs/ROADMAP_PROFESIONAL.md",
    "- validar la estrategia normativa de ampacidad base mediante Tablas 1/2 o equivalente formalmente validado (`P3C10`);\n",
    "- completar la revisión/promoción del primer candidato de `Iz_base` Tabla 2 y extender la estrategia primaria de Tablas 1/2 (`P3C10`);\n",
)

replace_once(
    "docs/ROADMAP_PROFESIONAL.md",
    "**Siguiente bloque principal:** P3C09, comenzando por un subconjunto pequeño de Tabla 5C verificado contra la copia oficial pinneada. El eje visual V3 permanece en paralelo; el pin de fuente por sí solo no cambia la evidencia de un modelo hasta que exista un dataset primario verificado.\n",
    "**Bloqueo humano actual:** P3C09 (Tabla 5C) y el primer candidato P3C10C (Tabla 2) ya disponen de evidencia reproducible, pero conservan revisión humana pendiente y no son `PRIMARY_VERIFIED`. Mientras esa barrera permanece correctamente cerrada, el siguiente bloque técnico automatizable es P3C11A: preparar evidencia primaria candidata para 5A/5B/5D/5E sin promover valores automáticamente. El eje visual V3 permanece en paralelo y ya distingue el origen de `Iz_base` de la evidencia de factores.\n",
)

path = Path("docs/P3C10_BASE_AMPACITY_STRATEGY.md")
text = path.read_text(encoding="utf-8")
append = '''

## P3C10C — primer candidato de Tabla 2

La fuente oficial pinneada fue recorrida de forma reproducible en GitHub Actions run `32880258067`. Se localizaron Tabla 1 en PDF 548–550, Tabla 2 en PDF 551–554 y la Tabla 3 de correspondencia método/columna en PDF 555.

Se registró el candidato mínimo `P3C10C_TABLE_2_XLPE_C_3C_70MM2_PRIMARY_REVIEW_CANDIDATE_V1` para método C, cobre, XLPE/EPR, 90 °C, tres conductores cargados y 70 mm². La Tabla 3 lo vincula a Tabla 2 Col. 23 y la evidencia candidata conserva `ampacity_a=229.0` desde PDF 552.

Este registro mantiene `manual_comparison_confirmed=false`, `human_reviewer=null`, `eligible_for_primary_dataset_pr=false` y `professional_emission=false`. Por tanto P3C10 sigue `PENDING`; P3C10C únicamente elimina la incertidumbre sobre estructura, página, columna y primer punto candidato.
'''
if "## P3C10C — primer candidato de Tabla 2" in text:
    raise SystemExit("P3C10C section already present")
path.write_text(text.rstrip() + append + "\n", encoding="utf-8")

print("P3C10C docs finalized")
