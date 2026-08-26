from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# ROADMAP maestro
path = ROOT / "docs" / "ROADMAP_PROFESIONAL.md"
text = path.read_text(encoding="utf-8")
text = text.replace(
    "| P3 — Ampacidad normativa | **EN PROGRESO — P3C01–P3C10 DONE; COBERTURA Y VALIDACIÓN FINAL PENDIENTES** | `Ib <= In <= Iz`, routing normativo y factores verificables |",
    "| P3 — Ampacidad normativa | **COMPLETA CON LIMITACIONES (P3 v1)** | `Ib <= In <= Iz`, routing normativo, evidencia primaria y benchmarks independientes |",
)
text = text.replace(
    "| P4 — IEC 60909 | PENDIENTE | cortocircuito formal validado |",
    "| P4 — IEC 60909 | **PENDIENTE — SIGUIENTE FASE PRINCIPAL** | cortocircuito formal validado |",
)
old_rule = "**Regla de avance:** salvo deuda técnica justificada, el siguiente bloque principal se toma de la primera fase no cerrada. P3 está en progreso y conserva `UNDER_VALIDATION`; no se avanzará formalmente a P4 hasta completar cobertura normativa, evidencia numérica primaria suficiente, benchmarks normativos primarios y el gate de salida P3 en estado `DONE`. Los ejes transversales V y E evolucionan en paralelo."
new_rule = "**Regla de avance:** salvo deuda técnica justificada, el siguiente bloque principal se toma de la primera fase no cerrada. P3-v1 queda cerrado en `READY_WITH_LIMITATIONS` con `P3C01–P3C13 = DONE`; P4 IEC 60909 pasa a ser la siguiente fase principal. Los ejes transversales V y E continúan evolucionando en paralelo y P3 puede ampliar cobertura de Tablas 1/2 de forma incremental sin reabrir el gate v1."
if old_rule not in text:
    raise SystemExit("No se encontró regla de avance antigua")
text = text.replace(old_rule, new_rule)
text = text.replace(
    "**Estado: EN PROGRESO — P3C01–P3C10 DONE; P3C11–P3C13 PENDIENTES.**",
    "**Estado: COMPLETA CON LIMITACIONES (P3 v1) — P3C01–P3C13 DONE.**",
)
text = text.replace(
    "`evaluar_cierre_p3()` separa el estado de la fase del estado del modelo y bloquea el paso formal a P4 mientras exista algún criterio P3-v1 pendiente.",
    "`evaluar_cierre_p3()` separa el estado de la fase del estado del modelo. Con `P3C01–P3C13 = DONE` devuelve `READY_WITH_LIMITATIONS` y habilita formalmente `P4_IEC_60909` como siguiente fase.",
)
start = text.find("Bloqueantes actuales:")
end = text.find("### Pendiente para cerrar P3", start)
if start < 0 or end < 0:
    raise SystemExit("No se encontró bloque de pendientes P3")
replacement = """Cierre final P3-v1:\n\n- `P3C11` — `DONE`: cobertura primaria declarada de Tablas 5A/5B/5C/5D/5E;\n- `P3C12` — `DONE`: suite independiente primaria P3C12A con 29/29 casos PASS y seis familias cubiertas;\n- `P3C13` — `DONE`: `validation_status.ampacity = VALIDATED_WITH_LIMITATIONS`.\n\nEl cierre P3-v1 no implica que toda fila de Tablas 1/2 esté cargada ni que cualquier combinación física tenga binding automático. Los casos fuera de evidencia exacta continúan `VALUE_NOT_TABULATED`, manuales o fail-closed según corresponda.\n\n### Limitaciones y trabajo incremental después de P3 v1\n\n"""
text = text[:start] + replacement + text[end + len("### Pendiente para cerrar P3\n\n"):]
text = text.replace(
    "- incorporar benchmarks independientes primarios por familia (`P3C12`);\n",
    "- ampliar benchmarks independientes cuando se amplíe el alcance de datasets/base;\n",
)
path.write_text(text, encoding="utf-8")

# P3 EXIT GATE: reescritura concisa y actual
path = ROOT / "docs" / "P3_EXIT_GATE.md"
path.write_text("""# P3 — Gate formal de salida de ampacidad\n\n## Estado\n\n**READY_WITH_LIMITATIONS — P3-v1 CERRADA.**\n\n`evaluar_cierre_p3()` separa la madurez/cobertura del producto del estado de un modelo concreto. Con los trece criterios `P3C01`–`P3C13` en `DONE`, el gate devuelve:\n\n```text\nphase_status = READY_WITH_LIMITATIONS\nready_for_next_phase = true\nnext_phase = P4_IEC_60909\nprofessional_emission = false\n```\n\n`professional_emission=false` es deliberado: cerrar P3 no sustituye el QA del modelo, la calidad de sus datos ni la revisión del ingeniero responsable.\n\n## Alcance P3-v1\n\n- jurisdicción: Perú;\n- referencia: `PERU_CNE_UTILIZACION_2006`;\n- perfil: `PERU_CNE_UTIL_2006_030_004`;\n- regla: 030-004;\n- métodos enrutados: A1, A2, B1, B2, C, D, E, F y G;\n- contrato: `Ib <= In <= Iz`, con `Iz = Iz_base * product(k_i)`.\n\n## Evidencia de cierre\n\n- P3C01–P3C07: contrato, router, datasets, evidencia, bindings, readiness y V3;\n- P3C08: fuente oficial MINEM/CNE pinneada por SHA-256;\n- P3C09: datasets numéricos `PRIMARY_VERIFIED`;\n- P3C10: estrategia `Iz_base` primaria exacta de Tablas 1/2 demostrada;\n- P3C11: cobertura primaria declarada de 5A/5B/5C/5D/5E;\n- P3C12: referencias primarias independientes, 29/29 casos PASS, seis familias;\n- P3C13: módulo `ampacity` elevado a `VALIDATED_WITH_LIMITATIONS`.\n\nFuente primaria pinneada:\n\n```text\nsource_id = MINEM_CNE_UTIL_2006_OFFICIAL_PDF\nexpected_sha256 = 2b3cbd457c519bf9d9aa2cf2754c72b6e531708e45ea2fdf91f839b1acccfd64\n```\n\n## Qué significa VALIDATED_WITH_LIMITATIONS\n\nP3-v1 es utilizable dentro de su alcance declarado, pero no equivale a una transcripción universal del CNE:\n\n1. Tablas 1/2 no están cargadas exhaustivamente; `Iz_base` profesional requiere coincidencia exacta con una fila `PRIMARY_VERIFIED`.\n2. No existe interpolación, extrapolación ni vecino más cercano.\n3. Cobertura primaria de una tabla no implica binding automático de toda combinación física.\n4. Tabla 5A mantiene fail-closed para columnas 20–25 por la inconsistencia editorial identificada.\n5. Datasets secundarios históricos requieren opt-in y nunca habilitan emisión profesional.\n6. IEC 60364-5-52:2009+AMD1:2024 continúa `REFERENCE_ONLY`.\n\n## Estado de modelo\n\nUn modelo concreto puede ser `MODEL_NOT_CONFIGURED`, `MODEL_NOT_READY` o `MODEL_TECHNICALLY_READY`. Su evidencia normativa se evalúa aparte. Por ello una fase P3 cerrada puede coexistir con un modelo que use evidencia secundaria y no sea apto para emisión.\n\n## Paso a P4\n\nP4 IEC 60909 queda formalmente habilitada como siguiente fase del roadmap. Esto no convierte el actual `OpenDSS FaultStudy` en IEC 60909: el módulo `short_circuit` permanece `UNDER_VALIDATION` hasta que P4 implemente y valide el método formal.\n""", encoding="utf-8")

# Roadmap visual
path = ROOT / "docs" / "ROADMAP_VISUAL.md"
text = path.read_text(encoding="utf-8")
text = text.replace(
    "**Estado: EN PROGRESO — FOUNDATION V3 + P3A + EVIDENCIA P3B + BASE NORMATIVA P3C10.**",
    "**Estado: COMPLETA CON LIMITACIONES (V3/P3-v1).**",
)
text = text.replace(
    "- aviso visible de madurez `UNDER_VALIDATION`;",
    "- aviso visible de madurez `VALIDATED_WITH_LIMITATIONS` y límites del alcance P3-v1;",
)
path.write_text(text, encoding="utf-8")

# README: estado global honesto antes del primer clon
path = ROOT / "README.md"
text = path.read_text(encoding="utf-8")
old = "> **Estado:** proyecto educativo / experimental. No sustituye un estudio\n> eléctrico profesional ni software validado para diseño, coordinación de\n> protecciones o seguridad de arco eléctrico."
new = "> **Estado:** plataforma en desarrollo con módulos en distintos niveles de madurez.\n> Flujo de potencia, caída de tensión, biblioteca de conductores y ampacidad P3-v1\n> están `VALIDATED_WITH_LIMITATIONS` dentro de alcances publicados. IEC 60909,\n> coordinación/TCC, IEEE 1584 y expediente profesional completo continúan pendientes.\n> La herramienta no sustituye la revisión ni responsabilidad del ingeniero."
if old not in text:
    raise SystemExit("No se encontró bloque de estado README")
text = text.replace(old, new)
path.write_text(text, encoding="utf-8")
