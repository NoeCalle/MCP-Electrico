"""Genera evidencia JSON del gate P7D Engineering Preview 0.9."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp_electrico import p7_completion


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="p7d_engineering_preview.json")
    args = parser.parse_args()

    result = p7_completion.evaluar_cierre_p7()
    target = Path(args.output).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))

    if not result.get("ready_for_release"):
        raise SystemExit("P7D gate NOT_READY")


if __name__ == "__main__":
    main()
