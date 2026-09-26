from __future__ import annotations

import ast
import json
from pathlib import Path

from mcp_electrico import real_project_dossier_tools


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts" / "public_first_use_v1.json"


def _contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _function_contract(source_file: str, function_name: str) -> dict:
    path = ROOT / source_file
    tree = ast.parse(path.read_text(encoding="utf-8"))
    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    ]
    assert len(matches) == 1, f"{function_name} must exist exactly once in {source_file}"
    fn = matches[0]

    args = [arg.arg for arg in fn.args.args]
    defaults = [None] * (len(args) - len(fn.args.defaults)) + list(fn.args.defaults)
    parameters = []
    for name, default_node in zip(args, defaults):
        if default_node is None:
            parameters.append({"name": name, "required": True})
        else:
            parameters.append(
                {
                    "name": name,
                    "required": False,
                    "default": ast.literal_eval(default_node),
                }
            )

    exposed = any(
        isinstance(dec, ast.Call)
        and isinstance(dec.func, ast.Attribute)
        and dec.func.attr == "tool"
        for dec in fn.decorator_list
    )
    return {"parameters": parameters, "mcp_tool_decorator": exposed}


def test_p11b_public_tool_names_and_signatures_are_backward_compatible():
    contract = _contract()

    assert contract["schema"] == "MCP_ELECTRICO_PUBLIC_FIRST_USE_CONTRACT_V1"
    assert contract["scope"] == "FIRST_USE_OPERATIONAL_SURFACE_ONLY"

    tools = contract["tools"]
    assert [item["name"] for item in tools] == contract["recommended_sequence"]

    for tool in tools:
        live = _function_contract(tool["source_file"], tool["name"])
        assert live["mcp_tool_decorator"] is True
        assert live["parameters"] == tool["parameters"]


def test_p11b_runtime_first_use_sequence_matches_versioned_contract():
    contract = _contract()
    runtime = real_project_dossier_tools.obtener_contrato_p8f4()

    sequence = runtime["recommended_sequence"]
    assert [item["tool"] for item in sequence] == contract["recommended_sequence"]
    assert sequence[0]["success_status"] == contract["success_statuses"]["admission"]
    assert sequence[1]["success_status"] == contract["success_statuses"]["dossier"]
    assert sequence[2]["success_status"] == contract["success_statuses"]["integrity"]

    safety = contract["safety_invariants"]
    for key in (
        "automatic_repair",
        "automatic_retry",
        "automatic_defaults",
        "automatic_dispatch",
        "automatic_fault_binding",
        "crosscheck",
        "professional_emission",
    ):
        assert runtime[key] is safety[key] is False


def test_p11b_integrity_and_collision_guarantees_match_runtime_contracts():
    contract = _contract()
    expected = contract["dossier_guarantees"]

    integrity = real_project_dossier_tools.obtener_contrato_p8f2()
    repeatability = real_project_dossier_tools.obtener_contrato_p8f3()

    assert integrity["hash_algorithm"] == expected["hash_algorithm"]
    assert integrity["portable_relative_paths"] is expected["portable_relative_paths"] is True
    assert integrity["exact_file_set_required"] is expected["exact_file_set_required"] is True

    assert repeatability["silent_overwrite"] is expected["silent_overwrite"] is False
    assert repeatability["output_collision_policy"] == expected["collision_policy"]
    assert repeatability["first_collision_suffix"] == expected["first_collision_suffix"]
    assert repeatability["prior_delivery_mutation_allowed"] is False
    assert repeatability["each_success_requires_independent_integrity_verification"] is True


def test_p11b_contract_changes_require_explicit_versioning_policy():
    policy = _contract()["compatibility_policy"]

    assert policy["remove_or_rename_tool_requires_contract_version_bump"] is True
    assert policy["add_or_remove_required_parameter_requires_contract_version_bump"] is True
    assert policy["change_public_default_requires_contract_version_bump"] is True
    assert policy["low_level_development_tools_frozen"] is False
