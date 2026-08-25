"""Registro versionado de referencias para P3.

Este archivo registra normas/fuentes; no copia tablas normativas protegidas ni
presenta una referencia registrada como motor de tablas implementado.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


NORMATIVE_REFERENCES: dict[str, dict[str, Any]] = {
    "IEC_60364_5_52_2009_A1_2024": {
        "id": "IEC_60364_5_52_2009_A1_2024",
        "title": "IEC 60364-5-52:2009+AMD1:2024",
        "edition": "3.1",
        "publication_date": "2024-11-22",
        "scope": "Low-voltage electrical installations - wiring systems",
        "publisher": "IEC",
        "official_url": "https://webstore.iec.ch/en/publication/103734",
        "reference_status": "REGISTERED",
        "automatic_tables": False,
        "note": "Referencia internacional vigente registrada; las tablas/factores no se reproducen ni se consideran implementados por este registro.",
    },
    "PERU_CNE_UTILIZACION_2006": {
        "id": "PERU_CNE_UTILIZACION_2006",
        "title": "Código Nacional de Electricidad - Utilización",
        "edition": "R.M. N.° 0037-2006-MEM",
        "publication_date": "2006-01-30",
        "effective_date": "2006-07-01",
        "scope": "Instalaciones eléctricas de utilización en Perú",
        "publisher": "Ministerio de Energía y Minas del Perú",
        "official_url": "https://www.gob.pe/institucion/minem/normas-legales/108855-0037-2006-mem",
        "reference_status": "REGISTERED",
        "automatic_tables": False,
        "note": "Referencia legal base registrada. P3 debe versionar también cualquier modificación/tabla específica utilizada antes de habilitar cálculo normativo automático.",
    },
}


def listar_referencias() -> list[dict[str, Any]]:
    return [deepcopy(value) for _, value in sorted(NORMATIVE_REFERENCES.items())]


def obtener_referencia(norm_id: str) -> dict[str, Any]:
    key = str(norm_id or "").strip().upper()
    try:
        return deepcopy(NORMATIVE_REFERENCES[key])
    except KeyError as exc:
        raise KeyError(
            f"Referencia normativa P3 no registrada: {norm_id}. Opciones: "
            + ", ".join(sorted(NORMATIVE_REFERENCES))
        ) from exc
