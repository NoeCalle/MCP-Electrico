"""Orquestador incremental Workspace V5.

V5 extiende V4 y después añade protección/TCC. No reemplaza las vistas previas
ni crea una segunda aplicación visual.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import (
    protection_curves,
    protection_data,
    workspace_p5_view,
    workspace_p8d2_view,
    workspace_v4,
)


def enhance_file(path: str | Path, snapshot: dict[str, Any]) -> dict[str, Any]:
    target = Path(path).expanduser()
    base = workspace_v4.enhance_file(target, snapshot)
    if not base.get("ok"):
        return base

    html = target.read_text(encoding="utf-8")
    protection_snapshot = protection_data.snapshot()
    datasets = protection_curves.listar_datasets()
    enhanced = workspace_p5_view.enhance_html(
        html,
        snapshot,
        protection_snapshot,
        datasets,
    )
    enhanced = workspace_p8d2_view.enhance_html(enhanced, snapshot)
    target.write_text(enhanced, encoding="utf-8")

    studies = snapshot.get("status", {}).get("studies", {})
    p5_keys = (*workspace_p5_view.STUDY_KEYS, workspace_p8d2_view.STUDY_KEY)
    return {
        **base,
        "workspace_version": 5,
        "p5_protection_view": workspace_p5_view.MARKER in enhanced,
        "p8d2_integrated_view": workspace_p8d2_view.MARKER in enhanced,
        "protection_device_count": len(protection_snapshot.get("devices") or []),
        "tcc_dataset_count": len(datasets),
        "p5_results_vigentes": {
            key: bool((studies.get(key) or {}).get("valid"))
            for key in p5_keys
        },
        "browser_engineering_calculation": False,
        "professional_emission": False,
    }
