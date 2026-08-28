from copy import deepcopy
import json
from pathlib import Path

from opendssdirect import dss

from mcp_electrico import (
    core,
    project_reconstruction,
    project_reconstruction_tools,
    project_snapshot,
    workspace_state,
)


def _source_snapshot(tmp_path, name="p7b_source") -> dict:
    core.crear_circuito(name, 0.48)
    workspace_state.reset_for_circuit("p7b_source")
    core.agregar_linea(
        "f1", "sourcebus", "bus1", 0.05,
        fases=3, r1_ohm_km=0.20, x1_ohm_km=0.08,
    )
    workspace_state.mark_model_changed("p7b_add_f1")
    core.agregar_carga("load1", "bus1", 60.0, 15.0, fases=3, kv=0.48)
    workspace_state.mark_model_changed("p7b_add_load1")
    workspace_state.record_study(
        "historical_probe",
        {"status": "STORED_ONLY", "professional_emission": False},
        "p7b_historical_probe",
    )
    return project_snapshot.construir_snapshot(str(tmp_path / "source_dss"))


def _sentinel(name="p7b_sentinel") -> None:
    core.crear_circuito(name, 0.22)
    workspace_state.reset_for_circuit("p7b_sentinel")


def _rehash(snapshot: dict) -> dict:
    updated = deepcopy(snapshot)
    updated["hash"]["value"] = project_snapshot._digest(updated["payload"])
    return updated


def test_p7b_valid_snapshot_reconstructs_and_roundtrip_matches(tmp_path):
    snapshot = _source_snapshot(tmp_path, "p7b_roundtrip")
    source_hash = snapshot["hash"]["value"]
    _sentinel()
    assert str(dss.Circuit.Name()) == "p7b_sentinel"

    result = project_reconstruction.reconstruir_snapshot(
        snapshot,
        directorio_reconstruccion=str(tmp_path / "reconstructed"),
    )

    assert result["status"] == "RECONSTRUCTED_NETLIST_VERIFIED_WITH_REBIND_REQUIRED"
    assert result["integrity"]["status"] == "HASH_MATCH"
    assert result["source_snapshot"]["hash"]["value"] == source_hash
    assert result["previous_circuit"] == "p7b_sentinel"
    assert result["reconstructed_circuit"] == "p7b_roundtrip"
    assert str(dss.Circuit.Name()) == "p7b_roundtrip"
    assert result["roundtrip"]["canonical_netlist_match"] is True
    assert result["restoration"]["netlist"] == "RESTORED_VERIFIED"
    assert result["restoration"]["professional_p2"] == "NOT_RESTORED_REQUIRES_REBIND"
    assert result["restoration"]["ampacity_p3"] == "NOT_RESTORED_REQUIRES_REBIND"
    assert result["restoration"]["protection_p5"] == "NOT_RESTORED_REQUIRES_REBIND"
    assert result["restoration"]["studies"] == "NOT_RESTORED_REQUIRES_RECALCULATION"
    assert result["stored_results_promoted_to_current"] is False
    assert result["workspace_status"]["studies"] == {}
    assert result["workspace_status"]["results_current"] is False
    assert result["engineering_preview_ready"] is False
    assert result["professional_emission"] is False


def test_p7b_hash_mismatch_does_not_write_or_touch_active_circuit(tmp_path):
    snapshot = _source_snapshot(tmp_path, "p7b_tamper_source")
    _sentinel("p7b_integrity_sentinel")
    tampered = deepcopy(snapshot)
    tampered["payload"]["project"]["circuit"] = "tampered"
    target = tmp_path / "must_not_exist"

    result = project_reconstruction.reconstruir_snapshot(
        tampered,
        directorio_reconstruccion=str(target),
    )

    assert result["status"] == "BLOCKED_SNAPSHOT_INTEGRITY"
    assert result["integrity"]["status"] == "HASH_MISMATCH"
    assert result["write_performed"] is False
    assert result["compile_performed"] is False
    assert str(dss.Circuit.Name()) == "p7b_integrity_sentinel"
    assert not target.exists()


def test_p7b_rejects_path_traversal_before_any_write(tmp_path):
    snapshot = _source_snapshot(tmp_path, "p7b_unsafe_source")
    unsafe = deepcopy(snapshot)
    files = unsafe["payload"]["netlist"]["files"]
    victim = next(item for item in files if item["name"].lower() != "master.dss")
    victim["name"] = "../escape.dss"
    unsafe = _rehash(unsafe)
    _sentinel("p7b_path_sentinel")
    target = tmp_path / "unsafe_target"

    result = project_reconstruction.reconstruir_snapshot(
        unsafe,
        directorio_reconstruccion=str(target),
    )

    assert result["integrity"]["status"] == "HASH_MATCH"
    assert result["status"] == "BLOCKED_INVALID_NETLIST"
    assert "P7B012" in result["error"]
    assert result["write_performed"] is False
    assert str(dss.Circuit.Name()) == "p7b_path_sentinel"
    assert not target.exists()


def test_p7b_rejects_missing_master_with_valid_hash(tmp_path):
    snapshot = _source_snapshot(tmp_path, "p7b_master_source")
    invalid = deepcopy(snapshot)
    invalid["payload"]["netlist"]["master_file"] = "MissingMaster.dss"
    invalid = _rehash(invalid)
    _sentinel("p7b_master_sentinel")

    result = project_reconstruction.reconstruir_snapshot(
        invalid,
        directorio_reconstruccion=str(tmp_path / "missing_master_target"),
    )
    assert result["status"] == "BLOCKED_INVALID_NETLIST"
    assert "P7B026" in result["error"]
    assert str(dss.Circuit.Name()) == "p7b_master_sentinel"


def test_p7b_roundtrip_mismatch_is_cleared_and_not_claimed(monkeypatch, tmp_path):
    snapshot = _source_snapshot(tmp_path, "p7b_mismatch_source")
    _sentinel("p7b_mismatch_sentinel")

    monkeypatch.setattr(
        project_snapshot,
        "construir_netlist_canonico",
        lambda _directory: {"master_file": "Master.dss", "file_count": 0, "files": []},
    )
    result = project_reconstruction.reconstruir_snapshot(
        snapshot,
        directorio_reconstruccion=str(tmp_path / "roundtrip_mismatch"),
    )

    assert result["status"] == "RECONSTRUCTION_ROUNDTRIP_MISMATCH"
    assert result["roundtrip"]["canonical_netlist_match"] is False
    assert result["restoration"]["netlist"] == "RESTORED_MISMATCH_CLEARED"
    assert result["stored_results_promoted_to_current"] is False
    assert result["active_circuit_after_failure"] == ""
    assert str(dss.Circuit.Name() or "") == ""
    assert result["professional_emission"] is False


def test_p7b_invalid_json_file_is_fail_closed(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{not-json", encoding="utf-8")
    _sentinel("p7b_json_sentinel")

    result = project_reconstruction.reconstruir_archivo(
        str(path),
        directorio_reconstruccion=str(tmp_path / "json_target"),
    )
    assert result["status"] == "INVALID_SNAPSHOT_JSON"
    assert result["stored_results_promoted_to_current"] is False
    assert str(dss.Circuit.Name()) == "p7b_json_sentinel"


def test_p7b_contract_and_public_tools_are_explicit():
    contract = project_reconstruction.obtener_contrato_p7b()
    assert contract["source_schema"] == "MCP_ELECTRICO_P7A_PROJECT_SNAPSHOT_V1"
    assert contract["integrity_before_write"] is True
    assert contract["stored_results_promoted_to_current"] is False
    assert contract["structured_state_auto_restore"] is False
    assert contract["professional_emission"] is False

    class FakeMCP:
        def __init__(self):
            self.names = []

        def tool(self):
            def decorator(func):
                self.names.append(func.__name__)
                return func
            return decorator

    fake = FakeMCP()
    project_reconstruction_tools.register(fake)
    assert fake.names == [
        "obtener_contrato_reconstruccion_p7b",
        "reconstruir_snapshot_proyecto_p7b",
        "reconstruir_archivo_proyecto_p7b",
    ]
