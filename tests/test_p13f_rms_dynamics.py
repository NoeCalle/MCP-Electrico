"""Migration gate: the old physics must not remain executable."""
from mcp_electrico import motor_dynamics as old

def test_legacy_dol_cannot_solve_or_silently_convert_inputs():
    assert not hasattr(old, 'electrical') and not hasattr(old, 'rk4')
    result = old.execute({}, {}, {})
    assert result['execution_status'] == 'RETIRED_CUSTOM_BACKEND'
    assert result['results'] == [] and not result['network_solve_performed']
    assert result['migration_requires_explicit_new_package']
    assert result['replacement_execution_tool'] == 'ejecutar_dinamica_modelica'
