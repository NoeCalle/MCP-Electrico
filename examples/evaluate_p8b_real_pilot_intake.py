"""Evalúa un manifiesto P8B sin construir ni modificar el modelo eléctrico."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp_electrico import real_pilot_intake


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="JSON con datos de admisión P8B")
    parser.add_argument("--output", default=None, help="JSON de resultado opcional")
    args = parser.parse_args()

    source = Path(args.input).expanduser().resolve()
    manifest = json.loads(source.read_text(encoding="utf-8"))
    result = real_pilot_intake.evaluar_admision(manifest)
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        target = Path(args.output).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
