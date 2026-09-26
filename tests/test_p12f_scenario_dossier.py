from __future__ import annotations

import json
from pathlib import Path

from mcp_electrico import (
    operating_scenario_dossier,
    operating_scenario_dossier_tools,
    professional_tools,
)


def _manifest() -> dict:
    path = Path(__file__).resolve().parents[1] / "examples" / "p10_reference_substation_stage1.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _package() -> dict:
    path = Path(__file__).resolve().parents[1] / "examples" / "p12e_alternative_source_transfer_reference.json"
    return json.loads(path.read_text(encoding="utf-8"))


class FakeMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(fn):
            assert fn.__name__ not in self.tools
            self.tools[fn.__name__] = fn
            return fn
        return decorator


def test_p12f_dossier_is_integral_collision_safe_and_tamper_evident(tmp_path):
    requested = tmp_path / "scenario_dossier"

    first = operating_scenario_dossier.generar_dossier(
        _manifest(),
        _package(),
        directorio_salida=str(requested),
    )

    assert first["schema"] == "MCP_ELECTRICO_P12F_SCENARIO_DOSSIER_V1"
    assert first["status"] == "SCENARIO_DOSSIER_READY"
    assert first["output_directory_collision_avoided"] is False
    assert first["summary"] == {
        "total": 1,
        "executed": 1,
        "pass": 1,
        "fail": 0,
        "blocked_or_error": 0,
    }
    assert first["workspace"]["ok"] is True
    assert first["workspace"]["browser_engineering_calculation"] is False
    assert first["p7a"]["status"] == "HASH_MATCH"
    assert first["p7b"]["status"] == "RECONSTRUCTED_NETLIST_VERIFIED_WITH_REBIND_REQUIRED"
    assert first["p7b"]["isolated_context"] is True
    assert first["p7b"]["parent_dss_context_mutated"] is False
    assert first["integrity"]["status"] == "SCENARIO_DOSSIER_INTEGRITY_VERIFIED"
    assert first["integrity"]["ok"] is True
    assert first["automatic_source_selection"] is False
    assert first["automatic_transfer"] is False
    assert first["professional_report"] is False
    assert first["professional_emission"] is False

    root = Path(first["output_directory"])
    expected = {
        "electrical_manifest.json",
        "scenario_package.json",
        "scenario_execution.json",
        "scenario_workspace.html",
        "scenario_report.html",
        "base_snapshot_p7a.json",
        "base_reconstruction_p7b.json",
        "scenario_dossier_integrity.json",
    }
    assert expected.issubset({item.name for item in root.iterdir()})
    assert (root / "p7a_netlist").is_dir()
    assert (root / "p7b_reconstructed").is_dir()

    workspace_html = (root / "scenario_workspace.html").read_text(encoding="utf-8")
    assert "MCP_ELECTRICO_P12F_SCENARIO_WORKSPACE" in workspace_html
    assert "SCN_TRANSFER_LV_TO_BACKUP" in workspace_html
    assert "El navegador no ejecuta cálculos eléctricos" in workspace_html

    first_verify = operating_scenario_dossier.verificar_integridad(
        first["integrity"]["index_path"]
    )
    assert first_verify["ok"] is True

    second = operating_scenario_dossier.generar_dossier(
        _manifest(),
        _package(),
        directorio_salida=str(requested),
    )
    assert second["status"] == "SCENARIO_DOSSIER_READY"
    assert second["output_directory_collision_avoided"] is True
    assert Path(second["output_directory"]).name == "scenario_dossier_2"

    first_verify_after_second = operating_scenario_dossier.verificar_integridad(
        first["integrity"]["index_path"]
    )
    assert first_verify_after_second["ok"] is True

    second_execution = Path(second["trace_files"]["scenario_execution"])
    second_execution.write_text(
        second_execution.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )
    tampered = operating_scenario_dossier.verificar_integridad(
        second["integrity"]["index_path"]
    )
    assert tampered["ok"] is False
    assert tampered["status"] == "SCENARIO_DOSSIER_INTEGRITY_MISMATCH"
    assert any(item["code"] in {"P12FVER011", "P12FVER012"} for item in tampered["issues"])


def test_p12f_blocks_artifacts_when_scenario_package_is_invalid(tmp_path):
    package = _package()
    package["scenarios"][0]["actions"] = list(reversed(package["scenarios"][0]["actions"]))

    result = operating_scenario_dossier.generar_dossier(
        _manifest(),
        package,
        directorio_salida=str(tmp_path / "blocked"),
    )

    assert result["status"] == "SCENARIO_DOSSIER_BLOCKED_BY_EXECUTION"
    assert result["artifact_generation_performed"] is False
    assert result["execution"]["execution_status"] == "SCENARIO_SET_EXECUTION_BLOCKED"
    assert result["professional_emission"] is False
    assert not (tmp_path / "blocked").exists()


def test_p12f_mcp_registry_exposes_dossier_without_second_engine(monkeypatch, tmp_path):
    contract = operating_scenario_dossier_tools.obtener_contrato_p12f()
    assert contract["tools"] == [
        "generar_dossier_escenarios_operativos",
        "verificar_integridad_dossier_escenarios",
    ]
    assert contract["automatic_source_selection"] is False
    assert contract["automatic_transfer"] is False
    assert contract["professional_emission"] is False

    mcp = FakeMCP()
    operating_scenario_dossier_tools.register(mcp)
    assert set(mcp.tools) == {
        "generar_dossier_escenarios_operativos",
        "verificar_integridad_dossier_escenarios",
    }

    calls = []

    def fake_generate(manifest, package, directorio_salida):
        calls.append(("generate", manifest, package, directorio_salida))
        return {"status": "SCENARIO_DOSSIER_READY", "professional_emission": False}

    def fake_verify(path):
        calls.append(("verify", path))
        return {"status": "SCENARIO_DOSSIER_INTEGRITY_VERIFIED", "ok": True}

    monkeypatch.setattr(
        operating_scenario_dossier_tools.operating_scenario_dossier,
        "generar_dossier",
        fake_generate,
    )
    monkeypatch.setattr(
        operating_scenario_dossier_tools.operating_scenario_dossier,
        "verificar_integridad",
        fake_verify,
    )

    generated = mcp.tools["generar_dossier_escenarios_operativos"](
        {"project": {"id": "TEST"}},
        {"project_id": "TEST"},
        str(tmp_path / "x"),
    )
    verified = mcp.tools["verificar_integridad_dossier_escenarios"]("x/index.json")
    assert generated["status"] == "SCENARIO_DOSSIER_READY"
    assert verified["ok"] is True
    assert calls[0][0] == "generate"
    assert calls[1] == ("verify", "x/index.json")

    all_tools = FakeMCP()
    professional_tools.register(all_tools)
    assert "generar_dossier_escenarios_operativos" in all_tools.tools
    assert "verificar_integridad_dossier_escenarios" in all_tools.tools
