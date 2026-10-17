"""Published phase-resolved transformer qualification through public entrypoints."""
from copy import deepcopy
import pytest
from opendssdirect import dss
import server
from mcp_electrico import core, real_model_materializer as builder
from scripts.transformer_reference import ieee_manifest, compare_ieee
from scripts.transformer_reference import tap_manifest, balanced_reference, compare_balanced


@pytest.mark.parametrize("direction", ["down", "up"])
@pytest.mark.parametrize("connection", ["ynyn", "dyn"])
@pytest.mark.parametrize("loading", ["balanced", "unbalanced"])
def test_published_ieee_transformers(direction, connection, loading):
    data = ieee_manifest(direction, connection, loading)
    built = builder.materializar_modelo(data)
    assert built["materializer_status"] == "MODEL_BUILT_NOT_EXECUTED", built
    flow = server.ejecutar_flujo_potencia()
    detail = server.analizar_flujo_operacion()
    comparison = compare_ieee(flow, detail, direction, connection, loading)
    assert comparison["passed"], comparison


@pytest.mark.parametrize("bad", [None, [], [[1,2]], [[True,0,0],[0,1,0],[0,0,1]],
    [[float("nan"),0,0],[0,1,0],[0,0,1]], [[1,2,0],[0,1,0],[0,0,1]],
    [[-1,0,0],[0,1,0],[0,0,1]]])
def test_invalid_matrix_does_not_mutate(bad):
    core.crear_circuito("preserved", .48)
    data = ieee_manifest()
    data["topology"]["lines"][0]["phase_impedance"]["r_ohm_km"] = bad
    result = builder.materializar_modelo(data)
    assert result["materializer_status"] == "BLOCKED_BY_MATERIALIZER_PREFLIGHT", result
    assert dss.Circuit.Name() == "preserved"


@pytest.mark.parametrize("nodes", [[0,0], [4,0], [1,2], [True,0], [1], "1.0", [1,False]])
def test_load_node_selection_rejected(nodes):
    core.crear_circuito("preserved", .48)
    data = ieee_manifest()
    data["topology"]["loads"][0]["nodes"] = nodes
    assert builder.materializar_modelo(data)["materializer_status"] == "BLOCKED_BY_MATERIALIZER_PREFLIGHT"
    assert dss.Circuit.Name() == "preserved"


def test_matrix_cannot_conflict_with_sequence_or_become_fault_model():
    for change in ("sequence", "boundary"):
        data = ieee_manifest()
        if change == "sequence":
            data["topology"]["lines"][0]["r1_ohm_km"] = .1
        else:
            data["source"].pop("power_flow_boundary")
        assert builder.materializar_modelo(data)["materializer_status"] == "BLOCKED_BY_MATERIALIZER_PREFLIGHT"


@pytest.mark.parametrize("group", ["Yy0", "Yyn0", "Dd0", "Dyn1", "Dyn11", "Yd1", "Yd11"])
@pytest.mark.parametrize("side", ["hv", "lv"])
@pytest.mark.parametrize("position", [-2,0,2])
def test_vector_groups_taps_losses_against_newton(group, side, position):
    pytest.importorskip("pypower")
    data = tap_manifest(group,side,position)
    assert builder.materializar_modelo(data)["materializer_status"] == "MODEL_BUILT_NOT_EXECUTED"
    comparison = compare_balanced(server.ejecutar_flujo_potencia(), balanced_reference(data))
    assert comparison["passed"], comparison


@pytest.mark.parametrize("side", ["hv", "lv"])
@pytest.mark.parametrize("position", [-2,0,2])
def test_explicit_excitation_losses(side, position):
    pytest.importorskip("pypower")
    data = tap_manifest("Dyn11",side,position,excitation=True)
    assert builder.materializar_modelo(data)["materializer_status"] == "MODEL_BUILT_NOT_EXECUTED"
    comparison = compare_balanced(server.ejecutar_flujo_potencia(), balanced_reference(data))
    assert comparison["passed"], comparison


@pytest.mark.parametrize("i0", [0., .01, float("nan"), float("inf"), True])
def test_inconsistent_no_load_current_rejected_before_mutation(i0):
    core.crear_circuito("preserved", .48)
    data = tap_manifest(excitation=True)
    data["topology"]["transformers"][0]["i0_percent"] = i0
    assert builder.materializar_modelo(data)["materializer_status"] == "BLOCKED_BY_MATERIALIZER_PREFLIGHT"
    assert dss.Circuit.Name() == "preserved"
