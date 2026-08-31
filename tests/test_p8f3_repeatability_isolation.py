from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import runpy

import pytest

from mcp_electrico import dossier_integrity, real_project_dossier, workspace_state


def _manifest() -> dict:
    fixture = runpy.run_path(str(Path(__file__).with_name("test_p8d2_real_protection_execution.py")))
    return fixture["_manifest"]()


def _file_sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def repeated_success(tmp_path_factory):
    root = tmp_path_factory.mktemp("p8f3-success")
    requested = root / "real_dossier"
    manifest = _manifest()

    first = real_project_dossier.generar_dossier(manifest, str(requested))
    assert first["status"] == "DOSSIER_READY_ENGINEERING_PREVIEW"
    first_dir = Path(first["output_directory"])
    first_index = first_dir / "dossier_integrity.json"
    first_index_sha_before = _file_sha(first_index)
    first_execution_sha_before = _file_sha(first_dir / "execution_p8d2.json")

    second = real_project_dossier.generar_dossier(manifest, str(requested))
    assert second["status"] == "DOSSIER_READY_ENGINEERING_PREVIEW"

    return {
        "requested": requested.resolve(),
        "first": first,
        "second": second,
        "first_dir": first_dir,
        "second_dir": Path(second["output_directory"]),
        "first_index_sha_before": first_index_sha_before,
        "first_execution_sha_before": first_execution_sha_before,
    }


@pytest.fixture(scope="module")
def success_then_blocked(tmp_path_factory):
    root = tmp_path_factory.mktemp("p8f3-blocked")
    requested = root / "real_dossier"
    manifest = _manifest()

    first = real_project_dossier.generar_dossier(manifest, str(requested))
    assert first["status"] == "DOSSIER_READY_ENGINEERING_PREVIEW"
    first_dir = Path(first["output_directory"])
    first_index_sha_before = _file_sha(first_dir / "dossier_integrity.json")

    invalid = _manifest()
    invalid["protection"].pop("fault_bindings")
    blocked = real_project_dossier.generar_dossier(invalid, str(requested))

    return {
        "requested": requested.resolve(),
        "first": first,
        "blocked": blocked,
        "first_dir": first_dir,
        "first_index_sha_before": first_index_sha_before,
    }


def test_p8f3_second_success_uses_new_directory_without_overwriting_first(repeated_success):
    data = repeated_success
    requested = data["requested"]
    first = data["first"]
    second = data["second"]

    assert Path(first["requested_output_directory"]) == requested
    assert Path(first["output_directory"]) == requested
    assert first["output_directory_collision_avoided"] is False

    assert Path(second["requested_output_directory"]) == requested
    assert Path(second["output_directory"]) == requested.with_name("real_dossier_2")
    assert second["output_directory_collision_avoided"] is True
    assert data["first_dir"] != data["second_dir"]
    assert data["first_dir"].is_dir()
    assert data["second_dir"].is_dir()


def test_p8f3_first_dossier_remains_byte_intact_and_verifiable_after_second(repeated_success):
    data = repeated_success
    first_dir = data["first_dir"]

    assert _file_sha(first_dir / "dossier_integrity.json") == data["first_index_sha_before"]
    assert _file_sha(first_dir / "execution_p8d2.json") == data["first_execution_sha_before"]
    verification = dossier_integrity.verificar_indice(first_dir / "dossier_integrity.json")
    assert verification["status"] == "DOSSIER_INTEGRITY_VERIFIED"
    assert verification["ok"] is True


def test_p8f3_both_successful_dossiers_are_independently_verifiable(repeated_success):
    data = repeated_success
    for result, directory in (
        (data["first"], data["first_dir"]),
        (data["second"], data["second_dir"]),
    ):
        verification = dossier_integrity.verificar_indice(directory / "dossier_integrity.json")
        assert result["integrity"]["status"] == "DOSSIER_INTEGRITY_VERIFIED"
        assert verification["status"] == "DOSSIER_INTEGRITY_VERIFIED"
        assert verification["ok"] is True
        assert result["p7a"]["status"] == "HASH_MATCH"
        assert result["p7b"]["status"] == "RECONSTRUCTED_NETLIST_VERIFIED_WITH_REBIND_REQUIRED"
        assert result["p7c"]["status"] == "TECHNICAL_REPORT_READY_FOR_PRINT"


def test_p8f3_same_manifest_keeps_same_manifest_hash_but_current_state_is_latest_run(repeated_success):
    data = repeated_success
    first = data["first"]
    second = data["second"]

    assert first["manifest_sha256"] == second["manifest_sha256"]
    assert workspace_state.status()["model_revision"] == second["model_revision"]
    assert workspace_state.status()["studies"]["protection_tcc"]["valid"] is True
    assert workspace_state.status()["studies"]["protection_tcc"]["model_revision"] == second["model_revision"]

    # P8F3 no exige hashes P7A idénticos entre corridas: cada ejecución puede
    # tener una revisión de modelo distinta, pero cada dossier debe verificarse.
    assert first["p7a"]["status"] == "HASH_MATCH"
    assert second["p7a"]["status"] == "HASH_MATCH"


def test_p8f3_blocked_second_attempt_creates_no_new_delivery_and_preserves_first_dossier(success_then_blocked):
    data = success_then_blocked
    blocked = data["blocked"]
    requested = data["requested"]
    first_dir = data["first_dir"]

    assert blocked["status"] == "BLOCKED_BY_P8D2_EXECUTION"
    assert Path(blocked["requested_output_directory"]) == requested
    assert blocked["output_directory"] is None
    assert blocked["output_directory_collision_avoided"] is False
    assert blocked["artifact_generation_performed"] is False
    assert blocked["integrity_index_generated"] is False
    assert not requested.with_name("real_dossier_2").exists()

    assert _file_sha(first_dir / "dossier_integrity.json") == data["first_index_sha_before"]
    verification = dossier_integrity.verificar_indice(first_dir / "dossier_integrity.json")
    assert verification["status"] == "DOSSIER_INTEGRITY_VERIFIED"
    assert verification["ok"] is True

    # El intento bloqueado es el estado lógico más reciente: P8D2 limpia los
    # estudios visibles previos en vez de aparentar que pertenecen al intento.
    assert workspace_state.status()["studies"] == {}


def test_p8f3_keeps_automatic_behaviour_closed(repeated_success):
    for result in (repeated_success["first"], repeated_success["second"]):
        assert result["automatic_dispatch"] is False
        assert result["automatic_fault_binding"] is False
        assert result["p4_recalculation_inside_p5"] is False
        assert result["crosscheck"] is False
        assert result["professional_emission"] is False
