from copy import deepcopy
import json
from pathlib import Path

from mcp_electrico import core, project_snapshot, project_snapshot_tools, workspace_state


def _case(name: str = "p7a") -> None:
    core.crear_circuito(name, 0.48)
    workspace_state.reset_for_circuit("p7a_test")
    core.agregar_linea(
        "f1", "sourcebus", "bus1", 0.05,
        fases=3, r1_ohm_km=0.20, x1_ohm_km=0.08,
    )
    workspace_state.mark_model_changed("p7a_add_f1")
    core.agregar_carga("load1", "bus1", 60.0, 15.0, fases=3, kv=0.48)
    workspace_state.mark_model_changed("p7a_add_load1")


def test_p7a_same_state_same_hash_and_no_export_paths(tmp_path):
    _case("p7a_deterministic")
    first = project_snapshot.construir_snapshot(str(tmp_path / "dss_a"))
    second = project_snapshot.construir_snapshot(str(tmp_path / "dss_b"))

    assert first["schema"] == "MCP_ELECTRICO_P7A_PROJECT_SNAPSHOT_V1"
    assert first["hash"]["algorithm"] == "sha256"
    assert first["hash"]["value"] == second["hash"]["value"]
    assert len(first["hash"]["value"]) == 64
    assert first["payload"] == second["payload"]

    netlist = first["payload"]["netlist"]
    assert netlist["paths_included"] is False
    assert netlist["file_count"] >= 1
    assert all(set(item) == {"name", "content"} for item in netlist["files"])
    assert str(tmp_path) not in json.dumps(netlist, ensure_ascii=False)
    assert "last_update" not in json.dumps(first["payload"], ensure_ascii=False)
    assert "recorded_at" not in json.dumps(first["payload"], ensure_ascii=False)


def test_p7a_model_change_changes_hash(tmp_path):
    _case("p7a_hash_change")
    before = project_snapshot.construir_snapshot(str(tmp_path / "before"))

    core.agregar_linea(
        "f2", "bus1", "bus2", 0.03,
        fases=3, r1_ohm_km=0.25, x1_ohm_km=0.09,
    )
    workspace_state.mark_model_changed("p7a_add_f2")
    after = project_snapshot.construir_snapshot(str(tmp_path / "after"))

    assert before["hash"]["value"] != after["hash"]["value"]
    assert before["payload"]["project"]["model_revision"] != after["payload"]["project"]["model_revision"]


def test_p7a_contains_governance_and_engineering_layers(tmp_path):
    _case("p7a_layers")
    snapshot = project_snapshot.construir_snapshot(str(tmp_path / "dss"))
    payload = snapshot["payload"]

    assert set(payload["engineering_data"]) == {
        "professional_p2",
        "zero_sequence_p2",
        "ampacity_p3",
        "protection_p5",
        "tcc_datasets_p5",
    }
    governance = payload["governance"]
    assert "validation_matrix" in governance
    assert "limitations" in governance
    assert "p5_completion" in governance
    assert governance["p5_completion"]["phase_status"] == "READY_WITH_LIMITATIONS"
    assert governance["automatic_dispatch"] is False
    assert governance["crosscheck"] is False
    assert governance["professional_emission"] is False
    assert governance["runtime_versions"]["engine_contract"]["automatic_dispatch"] is False
    assert payload["p7_status"]["reconstruction_import"] == "NOT_IMPLEMENTED_P7A"
    assert payload["p7_status"]["engineering_preview_ready"] is False
    assert snapshot["professional_emission"] is False


def test_p7a_hash_verification_detects_tampering(tmp_path):
    _case("p7a_tamper")
    snapshot = project_snapshot.construir_snapshot(str(tmp_path / "dss"))
    valid = project_snapshot.verificar_snapshot(snapshot)
    assert valid["ok"] is True
    assert valid["status"] == "HASH_MATCH"
    assert valid["reconstruction_performed"] is False

    tampered = deepcopy(snapshot)
    tampered["payload"]["project"]["circuit"] = "altered"
    invalid = project_snapshot.verificar_snapshot(tampered)
    assert invalid["ok"] is False
    assert invalid["status"] == "HASH_MISMATCH"
    assert invalid["expected_hash"] != invalid["actual_hash"]


def test_p7a_export_never_overwrites_and_file_verifies(tmp_path):
    _case("p7a_export")
    requested = tmp_path / "project.json"
    first = project_snapshot.exportar_snapshot(
        ruta_salida=str(requested),
        directorio_netlist=str(tmp_path / "dss_1"),
    )
    second = project_snapshot.exportar_snapshot(
        ruta_salida=str(requested),
        directorio_netlist=str(tmp_path / "dss_2"),
    )

    assert first["ok"] is True
    assert second["ok"] is True
    assert Path(first["path"]).name == "project.json"
    assert Path(second["path"]).name == "project_2.json"
    assert first["hash"]["value"] == second["hash"]["value"]

    stored = json.loads(Path(first["path"]).read_text(encoding="utf-8"))
    assert project_snapshot.verificar_snapshot(stored)["status"] == "HASH_MATCH"


def test_p7a_public_tools_are_narrow_and_do_not_import_model():
    class FakeMCP:
        def __init__(self):
            self.names = []

        def tool(self):
            def decorator(func):
                self.names.append(func.__name__)
                return func
            return decorator

    fake = FakeMCP()
    project_snapshot_tools.register(fake)
    assert fake.names == [
        "construir_snapshot_proyecto_p7a",
        "exportar_snapshot_proyecto_p7a",
        "verificar_snapshot_proyecto_p7a",
    ]
    assert not any("import" in name.lower() or "reconstru" in name.lower() for name in fake.names)
