from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 1) Fuente única de verdad para la madurez de ampacidad.
path = ROOT / "mcp_electrico" / "ampacity.py"
text = path.read_text(encoding="utf-8")
text = text.replace(
    "    studies,\n)",
    "    studies,\n    validation_status,\n)",
    1,
)
marker = '_normative_routes: dict[str, dict[str, Any]] = {}\n\n\n'
if marker not in text:
    raise SystemExit("No se encontró marcador para helper de madurez")
text = text.replace(
    marker,
    marker + 'def _maturity() -> str:\n    return str(validation_status.get_module_status("ampacity")["status"])\n\n\n',
    1,
)
text = text.replace('"maturity": "UNDER_VALIDATION"', '"maturity": _maturity()')
text = text.replace(
    '"La madurez P3 continúa UNDER_VALIDATION y professional_emission permanece false."',
    'f"La madurez P3-v1 es {_maturity()} dentro de su alcance y professional_emission permanece false para el resultado global."',
)
text = text.replace(
    '"la madurez continúa UNDER_VALIDATION y P3C11 sigue con cobertura normativa parcial."',
    'f"la madurez P3-v1 es {_maturity()} con límites explícitos; la aptitud profesional depende del modelo concreto."',
)
path.write_text(text, encoding="utf-8")

# 2) Contratos que ya deben reflejar cierre P3C13.
path = ROOT / "tests" / "test_ampacity_p3.py"
text = path.read_text(encoding="utf-8")
text = text.replace('assert "verificación primaria" in limitations', 'assert "tablas 1/2" in limitations\n    assert "fail-closed" in limitations')
path.write_text(text, encoding="utf-8")

path = ROOT / "tests" / "test_p3c12b_primary_benchmark_gate.py"
text = path.read_text(encoding="utf-8")
text = text.replace(
    'assert {item["id"] for item in gate["pending_criteria"]} == {"P3C13"}',
    'assert {item["id"] for item in gate["pending_criteria"]} == set()',
)
path.write_text(text, encoding="utf-8")

# 3) Reponer referencias trazables útiles en los documentos de cierre.
path = ROOT / "docs" / "P3_EXIT_GATE.md"
text = path.read_text(encoding="utf-8")
needle = "- P3C12: referencias primarias independientes, 29/29 casos PASS, seis familias;\n"
if needle not in text:
    raise SystemExit("No se encontró P3C12 en P3_EXIT_GATE")
text = text.replace(
    needle,
    needle + "  el gate deriva esta cobertura mediante `ampacity_benchmark_evidence.evaluar_cobertura()` y vuelve a comprobar la suite independiente viva;\n",
)
needle2 = "- P3C10: estrategia `Iz_base` primaria exacta de Tablas 1/2 demostrada;\n"
text = text.replace(
    needle2,
    needle2 + "  caso de referencia: `PERU_CNE_UTIL_2006_TABLE_2_COL23_C_XLPE_3C_CU_70MM2_PRIMARY_V1` (método C, 70 mm², 229 A);\n",
)
path.write_text(text, encoding="utf-8")

path = ROOT / "docs" / "ROADMAP_VISUAL.md"
text = path.read_text(encoding="utf-8")
needle = "**Estado: COMPLETA CON LIMITACIONES (V3/P3-v1).**"
if needle not in text:
    raise SystemExit("No se encontró estado V3")
text = text.replace(
    needle,
    needle + "\n\nHito conservado: **BASE NORMATIVA P3C10** visible y trazable en V3; el cierre P3C13 no elimina esa evidencia histórica.",
    1,
)
path.write_text(text, encoding="utf-8")
