"""Orquestador incremental del workspace V4.

Primero aplica la extensión V3 existente y luego añade la vista P4. Esto evita
que P4 duplique o reimplemente flujo, caída, P2 o ampacidad.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import workspace_p4_view, workspace_studies_view


def enhance_file(path: str | Path, snapshot: dict[str, Any]) -> dict[str, Any]:
    target = Path(path).expanduser()
    base = workspace_studies_view.enhance_file(target, snapshot)
    if not base.get("ok"):
        return base

    html = target.read_text(encoding="utf-8")
    enhanced = workspace_p4_view.enhance_html(html, snapshot)
    target.write_text(enhanced, encoding="utf-8")

    studies = snapshot.get("status", {}).get("studies", {})
    study_3ph = studies.get("iec60909_3ph") or {}
    study_2ph = studies.get("iec60909_2ph") or {}
    study_1ph_ground = studies.get("iec60909_1ph_ground") or {}
    return {
        **base,
        "workspace_version": 4,
        "p4_short_circuit_view": workspace_p4_view.MARKER in enhanced,
        "iec60909_3ph_vigente": bool(study_3ph and study_3ph.get("valid")),
        "iec60909_2ph_vigente": bool(study_2ph and study_2ph.get("valid")),
        "iec60909_1ph_ground_vigente": bool(
            study_1ph_ground and study_1ph_ground.get("valid")
        ),
    }
