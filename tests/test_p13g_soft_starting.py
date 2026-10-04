"""Migration gate for removal of the duplicated SCR/RL surrogate."""
from mcp_electrico import motor_soft_starting as old
from mcp_electrico import motor_soft_starting_dossier as dossier

def test_no_surrogate_physics_or_fallback_remains(tmp_path):
    assert not hasattr(old, 'phase_response') and not hasattr(old, 'alpha_for_gain')
    result = old.execute({}, {}, {}, {})
    assert result['execution_status'] == 'RETIRED_CUSTOM_BACKEND'
    assert result['results'] == [] and not result['ready_for_execution']
    blocked = dossier.generate({}, {}, {}, {}, tmp_path/'legacy')
    assert blocked['status'] == 'SOFT_STARTER_DOSSIER_BLOCKED'
    assert not (tmp_path/'legacy').exists()
