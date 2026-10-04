from pathlib import Path
from mcp_electrico import module_qualification as q,validation_status,engine_selection,reactive_compensation

ROOT=Path(__file__).resolve().parents[1]


def test_published_qualification_register_matches_runtime_registry():
    from scripts.render_module_qualification import render
    assert (ROOT/'docs/ESTADO_CIERRE_MODULOS.md').read_text(encoding='utf8') == render(q.catalogue())


def test_current_qualifications_have_evidence_and_finite_pending_gates():
    data=q.catalogue()
    for name,item in data['modules'].items():
        assert item['scope'] and item['evidence'],name
        assert all((ROOT/path).is_file() for path in item['evidence']),name
        assert not item['professional_emission']
        if item['verification_status']==q.VERIFIED:assert not item['closure_gates'],name
        if item['verification_status']=='IN_VERIFICATION':
            assert item['closure_gates'] and all(g['id'] and g['acceptance'] and g['status']=='PENDING' for g in item['closure_gates']),name


def test_scoped_promotion_does_not_promote_data_normative_or_report_approval():
    matrix=validation_status.get_validation_matrix()
    for name in ['reactive_compensation','protection_data','tcc_curve_evaluation','protection_checks','protection_clearing_time','protection_coordination','reproducible_project','project_reconstruction','technical_report']:
        assert matrix[name]['status']=='VALIDATED_WITH_LIMITATIONS'
        assert matrix[name]['previous_maturity_status']=='EXPERIMENTAL'
        assert matrix[name]['integration_verification']==q.VERIFIED
        assert not matrix[name]['qualification']['professional_emission']
        assert matrix[name]['qualification']['project_data_readiness']=='EVALUATED_PER_REQUEST'
    assert matrix['professional_report']['status']=='NOT_IMPLEMENTED'
    assert q.get('modelica_scr')['verification_status']=='IN_VERIFICATION'
    assert q.get('arc_flash_ieee1584')['verification_status']=='DEFERRED_BY_USER'


def test_catalogue_and_public_matrix_are_independent_copies():
    data=q.catalogue();data['modules']['modelica_dol']['closure_gates'].clear()
    assert q.get('modelica_dol')['closure_gates']
    matrix=engine_selection.obtener_capacidades_motores()
    assert matrix['matrix_revision']==q.catalogue()['revision']
    assert matrix['studies']['reactive_compensation']['qualification']['verification_status']==q.VERIFIED
    assert not matrix['crosscheck'] and not matrix['automatic_dispatch']
    assert reactive_compensation.contract()['maturity']=='VALIDATED_WITH_LIMITATIONS'
