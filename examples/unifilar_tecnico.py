"""Ejemplo visual: unifilar técnico con simbología eléctrica.

Genera ``unifilar_tecnico.html`` y ``unifilar_tecnico.svg``. Los símbolos ATS
y UPS del alimentador crítico son anotaciones visuales; no modifican el
modelo eléctrico OpenDSS de esta versión.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import server


def main() -> None:
    server.crear_circuito("hospital_unifilar", 22.9)
    server.agregar_transformador(
        "tr_01",
        "sourcebus",
        "tgbt",
        kva=500,
        kv_primario=22.9,
        kv_secundario=0.48,
        conexion_primario="delta",
        conexion_secundario="wye",
    )

    server.agregar_linea("f_motor", "tgbt", "mcc_01", 0.035, r1_ohm_km=0.25, x1_ohm_km=0.12)
    server.agregar_linea("f_alumbrado", "tgbt", "tpl_01", 0.025, r1_ohm_km=0.30, x1_ohm_km=0.12)
    server.agregar_linea("f_critico", "tgbt", "tcrit_01", 0.040, r1_ohm_km=0.22, x1_ohm_km=0.11)

    server.agregar_carga("motor_bomba", "mcc_01", 75, 30, kv=0.48, tipo_visual="motor")
    server.agregar_carga("alumbrado", "tpl_01", 40, 10, kv=0.48, tipo_visual="tablero")
    server.agregar_carga("cargas_criticas", "tcrit_01", 80, 25, kv=0.48, critica=True, tipo_visual="tablero")

    server.agregar_generador_respaldo("ge_01", "tcrit_01", 100, 0.48)
    server.configurar_alimentador_unifilar(
        "Line.f_critico",
        etiqueta="F-03",
        dispositivos=["ats", "ups"],
        fuente_alterna="Generator.ge_01",
    )
    server.configurar_alimentador_unifilar("Line.f_motor", etiqueta="F-01")
    server.configurar_alimentador_unifilar("Line.f_alumbrado", etiqueta="F-02")

    server.ejecutar_flujo_potencia()
    resultado = server.generar_diagrama_unifilar(
        "unifilar_tecnico.html",
        mostrar_leyenda=True,
        titulo="Hospital — Diagrama unifilar",
    )
    print(resultado)


if __name__ == "__main__":
    main()
