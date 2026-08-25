from pathlib import Path


# V3: conservar palabra completa para legibilidad y compatibilidad de contrato visual.
workspace = Path("mcp_electrico/workspace_p3_view.py")
text = workspace.read_text(encoding="utf-8")
if text.count("<th>Evid. factores</th>") != 1:
    raise SystemExit("P3C10B CI fix refused: visual heading anchor mismatch")
workspace.write_text(
    text.replace("<th>Evid. factores</th>", "<th>Evidencia factores</th>", 1),
    encoding="utf-8",
)

# Readiness: el caso positivo ahora debe declarar también evidencia primaria de Iz_base.
test_file = Path("tests/test_ampacity_evidence_readiness.py")
test = test_file.read_text(encoding="utf-8")
old_name = "def test_perfil_sintetico_totalmente_primario_clasifica_ready_sin_habilitar_emision_global():"
new_name = "def test_base_y_factores_primarios_clasifican_ready_sin_habilitar_emision_global():"
if test.count(old_name) != 1:
    raise SystemExit("P3C10B CI fix refused: readiness test name anchor mismatch")
test = test.replace(old_name, new_name, 1)

old_profile = '''    profile = {
        "element": "Line.synthetic",
        "correction": {
'''
new_profile = '''    profile = {
        "element": "Line.synthetic",
        "base": {
            "evidence": {
                "origin": "P3B_BASE_DATASET",
                "normative_base": True,
                "primary": True,
                "professional_emission": True,
            },
        },
        "correction": {
'''
if test.count(old_profile) != 1:
    raise SystemExit("P3C10B CI fix refused: readiness profile anchor mismatch")
test = test.replace(old_profile, new_profile, 1)

extra = '''


def test_factores_primarios_sin_base_normativa_no_completan_evidencia():
    profile = {
        "element": "Line.synthetic_without_base",
        "correction": {
            "mode": "EXPLICIT_FACTORS",
            "factors": [{"origin": "P3B_DATASET"}],
            "factor_evidence": {
                "total": 1,
                "manual": 0,
                "dataset_primary": 1,
                "dataset_secondary": 0,
                "contains_secondary": False,
                "professional_factor_evidence": True,
                "automatic_normative_lookup": True,
            },
        },
    }
    result = ampacity_evidence_readiness._profile_status(profile)
    assert result["status"] == "EVIDENCE_INCOMPLETE"
    assert result["professional_normative_evidence_ready"] is False
    assert "Iz_base" in result["reasons"][0]
'''
if "test_factores_primarios_sin_base_normativa_no_completan_evidencia" in test:
    raise SystemExit("P3C10B CI fix refused: extra test already exists")
test_file.write_text(test.rstrip() + extra + "\n", encoding="utf-8")

print("P3C10B CI contracts updated")
