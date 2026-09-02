from __future__ import annotations

from copy import deepcopy

from opendssdirect import dss

from mcp_electrico import core, project_reconstruction, project_snapshot, workspace_state


def _source_snapshot(tmp_path) -> dict:
    core.crear_circuito("p7b_context_source", 0.48)
    workspace_state.reset_for_circuit("p7b_context_source")
    core.agregar_linea(
        "f1",
        "sourcebus",
        "bus1",
        0.05,
        fases=3,
        r1_ohm_km=0.20,
        x1_ohm_km=0.08,
    )
    workspace_state.mark_model_changed("p7b_context_add_line")
    core.agregar_carga("load1", "bus1", 60.0, 15.0, fases=3, kv=0.48)
    workspace_state.mark_model_changed("p7b_context_add_load")
    return project_snapshot.construir_snapshot(str(tmp_path / "source_dss"))


def test_p7b_new_context_roundtrip_preserves_parent_dss_and_workspace(tmp_path):
    snapshot = _source_snapshot(tmp_path)

    core.crear_circuito("p7b_parent_sentinel", 0.22)
    workspace_state.reset_for_circuit("p7b_parent_sentinel")
    workspace_state.record_study(
        "sentinel_study",
        {"status": "PARENT_ONLY", "professional_emission": False},
        "p7b_parent_probe",
    )
    parent_circuit = str(dss.Circuit.Name() or "")
    parent_status = deepcopy(workspace_state.status())

    result = project_reconstruction.reconstruir_snapshot_contexto_aislado(
        snapshot,
        directorio_reconstruccion=str(tmp_path / "isolated_reconstructed"),
    )

    assert result["status"] == "RECONSTRUCTED_NETLIST_VERIFIED_WITH_REBIND_REQUIRED"
    assert result["roundtrip"]["canonical_netlist_match"] is True
    assert result["reconstructed_circuit"] == "p7b_context_source"
    assert result["isolation_mode"] == "OPENDSS_NEW_CONTEXT"
    assert result["isolated_context"] is True
    assert result["isolated_process"] is False
    assert result["parent_dss_context_mutated"] is False
    assert result["parent_structured_state_mutated"] is False
    assert result["stored_results_promoted_to_current"] is False

    assert str(dss.Circuit.Name() or "") == parent_circuit == "p7b_parent_sentinel"
    assert workspace_state.status() == parent_status
    assert workspace_state.status()["studies"]["sentinel_study"]["valid"] is True


def test_p7b_new_context_integrity_failure_never_touches_parent(tmp_path):
    snapshot = _source_snapshot(tmp_path)
    tampered = deepcopy(snapshot)
    tampered["payload"]["project"]["circuit"] = "tampered"

    core.crear_circuito("p7b_parent_integrity_sentinel", 0.22)
    workspace_state.reset_for_circuit("p7b_parent_integrity_sentinel")
    parent_status = deepcopy(workspace_state.status())

    result = project_reconstruction.reconstruir_snapshot_contexto_aislado(
        tampered,
        directorio_reconstruccion=str(tmp_path / "must_not_materialize"),
    )

    assert result["status"] == "BLOCKED_SNAPSHOT_INTEGRITY"
    assert result["integrity"]["status"] == "HASH_MISMATCH"
    assert result["isolation_mode"] == "OPENDSS_NEW_CONTEXT"
    assert result["isolated_context"] is True
    assert str(dss.Circuit.Name() or "") == "p7b_parent_integrity_sentinel"
    assert workspace_state.status() == parent_status
