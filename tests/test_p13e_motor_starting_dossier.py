from __future__ import annotations

import json
from pathlib import Path

from mcp_electrico import (
    motor_starting_dossier,
    motor_starting_sequences,
    motor_starting_workspace,
)


ROOT = Path(__file__).resolve().parents[1]


def _manifest() -> dict:
    return json.loads(
        (ROOT / "examples" / "p13_motor_starting_multi_stage3.json").read_text(encoding="utf-8")
    )


def _profiles() -> dict:
    return json.loads(
        (ROOT / "examples" / "p13_motor_starting_multi_profiles_stage3.json").read_text(encoding="utf-8")
    )


def _sequences() -> dict:
    return json.loads(
        (ROOT / "examples" / "p13_motor_starting_sequence_stage3.json").read_text(encoding="utf-8")
    )


def test_p13e_workspace_is_read_only_presentation(tmp_path):
    execution = motor_starting_sequences.ejecutar_secuencias(
        _manifest(),
        _profiles(),
        _sequences(),
    )
    assert execution["execution_status"] == "STATIC_MOTOR_SEQUENCE_COMPLETED"

    target = tmp_path / "motor_workspace.html"
    result = motor_starting_workspace.escribir_workspace(
        target,
        _manifest(),
        _profiles(),
        _sequences(),
        execution,
    )

    assert result["schema"] == "MCP_ELECTRICO_P13E_MOTOR_WORKSPACE_V1"
    assert result["browser_engineering_calculation"] is False
    assert result["professional_emission"] is False
    html = target.read_text(encoding="utf-8")
    assert "Motores y arranque P13E" in html
    assert "SEQ-M01-M02" in html
    assert "Motor.m01" in html
    assert "Motor.m02" in html
    assert 'id="p13e-data"' in html
    assert "El navegador no recalcula" in html


def test_p13e_dossier_contains_snapshot_reconstruction_and_integrity(tmp_path):
    requested = tmp_path / "motor_dossier"
    result = motor_starting_dossier.generar_dossier(
        _manifest(),
        _profiles(),
        _sequences(),
        directorio_salida=str(requested),
    )

    assert result["schema"] == "MCP_ELECTRICO_P13E_MOTOR_STARTING_DOSSIER_V1"
    assert result["status"] == "MOTOR_STARTING_DOSSIER_READY"
    assert result["execution_status"] == "STATIC_MOTOR_SEQUENCE_COMPLETED"
    assert result["artifact_generation_performed"] is True
    assert result["workspace"]["browser_engineering_calculation"] is False
    assert result["p7a"]["status"] == "HASH_MATCH"
    assert result["p7b"]["status"] == "RECONSTRUCTED_NETLIST_VERIFIED_WITH_REBIND_REQUIRED"
    assert result["p7b"]["isolated_context"] is True
    assert result["p7b"]["parent_dss_context_mutated"] is False
    assert result["integrity"]["status"] == "MOTOR_STARTING_DOSSIER_INTEGRITY_VERIFIED"
    assert result["integrity"]["ok"] is True
    assert result["professional_report"] is False
    assert result["professional_emission"] is False

    root = Path(result["output_directory"])
    for name in motor_starting_dossier.REQUIRED_TOP_LEVEL:
        assert (root / name).is_file()
    for name in motor_starting_dossier.REQUIRED_DIRECTORIES:
        assert (root / name).is_dir()
        assert any(path.is_file() for path in (root / name).rglob("*"))

    verification = motor_starting_dossier.verificar_integridad(
        root / motor_starting_dossier.INDEX_NAME
    )
    assert verification["ok"] is True
    assert verification["status"] == "MOTOR_STARTING_DOSSIER_INTEGRITY_VERIFIED"


def test_p13e_dossier_accepts_engineering_fail_as_valid_executed_result(tmp_path):
    manifest = _manifest()
    for study in manifest["studies"]:
        study["minimum_terminal_voltage_pu"] = 0.9999
        study["criterion_reference"] = (
            "CONTROLLED_REFERENCE_DATA - intentionally strict dossier criterion"
        )

    result = motor_starting_dossier.generar_dossier(
        manifest,
        _profiles(),
        _sequences(),
        directorio_salida=str(tmp_path / "strict_motor_dossier"),
    )

    assert result["status"] == "MOTOR_STARTING_DOSSIER_READY"
    assert result["execution_status"] == "STATIC_MOTOR_SEQUENCE_COMPLETED"
    assert any(item["status"] == "FAIL" for item in result["sequence_results"])
    assert result["integrity"]["ok"] is True


def test_p13e_dossier_is_collision_safe_and_preserves_first_delivery(tmp_path):
    requested = tmp_path / "motor_dossier"

    first = motor_starting_dossier.generar_dossier(
        _manifest(),
        _profiles(),
        _sequences(),
        directorio_salida=str(requested),
    )
    second = motor_starting_dossier.generar_dossier(
        _manifest(),
        _profiles(),
        _sequences(),
        directorio_salida=str(requested),
    )

    assert first["status"] == second["status"] == "MOTOR_STARTING_DOSSIER_READY"
    assert first["output_directory"] != second["output_directory"]
    assert first["output_directory_collision_avoided"] is False
    assert second["output_directory_collision_avoided"] is True

    first_index = Path(first["output_directory"]) / motor_starting_dossier.INDEX_NAME
    second_index = Path(second["output_directory"]) / motor_starting_dossier.INDEX_NAME
    assert motor_starting_dossier.verificar_integridad(first_index)["ok"] is True
    assert motor_starting_dossier.verificar_integridad(second_index)["ok"] is True


def test_p13e_integrity_detects_tampering(tmp_path):
    result = motor_starting_dossier.generar_dossier(
        _manifest(),
        _profiles(),
        _sequences(),
        directorio_salida=str(tmp_path / "motor_dossier"),
    )
    assert result["status"] == "MOTOR_STARTING_DOSSIER_READY"

    root = Path(result["output_directory"])
    execution_file = root / "motor_sequence_execution.json"
    execution_file.write_text(
        execution_file.read_text(encoding="utf-8") + "\nTAMPERED\n",
        encoding="utf-8",
    )

    verification = motor_starting_dossier.verificar_integridad(
        root / motor_starting_dossier.INDEX_NAME
    )
    assert verification["ok"] is False
    assert verification["status"] == "MOTOR_STARTING_DOSSIER_INTEGRITY_MISMATCH"
    assert any(
        issue["code"] in {"P13EVER011", "P13EVER012"}
        for issue in verification["issues"]
    )
