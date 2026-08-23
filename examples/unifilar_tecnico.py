"""Ejemplo de referencia: unifilar técnico v2.

Genera ``unifilar_tecnico.html`` y ``unifilar_tecnico.svg`` con una
representación limpia de ingeniería: una barra principal, alimentadores F-xx,
protecciones, datos selectivos y una rama crítica con ATS + UPS + GE.
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

    server.agregar_linea(
        "f_motor", "tgbt", "mcc_01", 0.035, r1_ohm_km=0.25, x1_ohm_km=0.12
    )
    server.agregar_linea(
        "f_alumbrado", "tgbt", "tpl_01", 0.025, r1_ohm_km=0.30, x1_ohm_km=0.12
    )
    server.agregar_linea(
        "f_critico", "tgbt", "tcrit_01", 0.040, r1_ohm_km=0.22, x1_ohm_km=0.11
    )

    server.agregar_carga(
        "motor_bomba", "mcc_01", 75, 30, kv=0.48, tipo_visual="motor"
    )
    server.agregar_carga(
        "alumbrado", "tpl_01", 40, 10, kv=0.48, tipo_visual="tablero"
    )
    server.agregar_carga(
        "cargas_criticas",
        "tcrit_01",
        80,
        25,
        kv=0.48,
        critica=True,
        tipo_visual="tablero",
    )

    server.agregar_generador_respaldo("ge_01", "tcrit_01", 100, 0.48)

    server.configurar_bus_unifilar("tgbt", rol="barra", etiqueta="TGBT")
    server.configurar_etiqueta_carga_unifilar(
        "motor_bomba", "M-01 · BOMBA AGUA"
    )
    server.configurar_etiqueta_carga_unifilar(
        "alumbrado", "TPL-01 · ALUMBRADO"
    )
    server.configurar_etiqueta_carga_unifilar(
        "cargas_criticas", "TABLERO CRÍTICO"
    )

    server.configurar_alimentador_unifilar(
        "Line.f_motor",
        etiqueta="F-01",
        proteccion="mccb",
        conductor="3×70 mm² Cu",
        corriente_nominal_a=160,
        capacidad_ruptura_ka=25,
    )
    server.configurar_alimentador_unifilar(
        "Line.f_alumbrado",
        etiqueta="F-02",
        proteccion="mccb",
        conductor="3×35 mm² Cu",
        corriente_nominal_a=100,
        capacidad_ruptura_ka=25,
    )
    server.configurar_alimentador_unifilar(
        "Line.f_critico",
        etiqueta="F-03",
        dispositivos=["ats", "ups"],
        fuente_alterna="Generator.ge_01",
        proteccion="mccb",
        conductor="3×50 mm² Cu",
        corriente_nominal_a=125,
        capacidad_ruptura_ka=25,
    )

    server.ejecutar_flujo_potencia()
    resultado = server.generar_diagrama_unifilar(
        "unifilar_tecnico.html",
        titulo="Hospital — Diagrama unifilar",
        mostrar_leyenda=False,
        modo="ingenieria",
        orientacion="vertical",
        mostrar_marca=False,
    )
    print(resultado)


if __name__ == "__main__":
    main()
