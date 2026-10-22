"""Fixed nominal ratios must be declared, never inferred from missing taps."""
import pytest
from opendssdirect import dss
from mcp_electrico import professional_data as p2, core, real_controlled_execution
from test_p8d1_real_controlled_execution import _manifest

def test_explicit_fixed_nominal_transformer_runs_through_real_pf_gate():
    manifest = _manifest(["POWER_FLOW"])
    transformer = manifest["topology"]["transformers"][0]
    transformer.update(tap_min=0, tap_max=0, tap_neutral=0, tap_pos=0, tap_step_percent=0.0)
    result = real_controlled_execution.ejecutar_controlado(manifest)
    assert result["execution_status"] == "CONTROLLED_EXECUTION_COMPLETED", result
    assert result["results"]["POWER_FLOW"]["powerflow"]["convergio"] is True
    record = p2.snapshot()["transformers"][0]
    assert record["tap"]["enabled"] is True
    assert record["tap"]["fixed_nominal"] is True
    dss.Transformers.Name("tr01")
    for winding in (1,2):
        dss.Transformers.Wdg(winding)
        assert dss.Transformers.Tap() == pytest.approx(1.0)

def test_omitted_taps_still_block_real_pf_gate():
    manifest = _manifest(["POWER_FLOW"])
    for key in ("tap_min","tap_max","tap_neutral","tap_pos","tap_side","tap_step_percent"):
        manifest["topology"]["transformers"][0].pop(key)
    result = real_controlled_execution.ejecutar_controlado(manifest)
    assert result["execution_status"] == "BLOCKED_BY_READINESS"

@pytest.mark.parametrize("positions",[
    {"tap_min":-1,"tap_max":1,"tap_neutral":0,"tap_pos":0},
    {"tap_min":0,"tap_max":1,"tap_neutral":0,"tap_pos":1},
    {"tap_min":1,"tap_max":1,"tap_neutral":1,"tap_pos":1},
])
def test_zero_step_does_not_admit_an_adjustable_or_non_neutral_schedule(positions):
    with pytest.raises(ValueError, match="P2TR021"):
        p2._tap_data("hv",positions["tap_neutral"],positions["tap_min"],positions["tap_max"],0.0,positions["tap_pos"])
