"""
Ejemplo: visualización del circuito hospitalario en condición normal y N-1.

Genera:
  - diagrama_normal.html
  - diagrama_contingencia.html

La contingencia se mantiene activa con restaurar=False para que el unifilar
pueda representar el elemento abierto y los buses sin camino a la fuente.
Luego se restaura mediante cerrar_elemento(), que también vuelve a resolver.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import server


def construir_modelo():
    server.crear_circuito("hospital_central", kv_base=13.2)
    server.agregar_transformador(
        nombre="trafo_principal",
        bus_primario="sourcebus",
        bus_secundario="tablero_general",
        kva=500,
        kv_primario=13.2,
        kv_secundario=0.4,
    )
    server.agregar_linea(
        nombre="alimentador_quirofanos",
        bus1="tablero_general",
        bus2="tablero_quirofanos",
        longitud_km=0.05,
        r1_ohm_km=0.5,
        x1_ohm_km=0.3,
    )
    server.agregar_carga(
        nombre="quirofanos",
        bus="tablero_quirofanos",
        kw=50,
        kvar=20,
        critica=True,
    )
    server.agregar_carga(
        nombre="iluminacion_general",
        bus="tablero_general",
        kw=20,
        kvar=5,
    )
    server.agregar_generador_respaldo(
        nombre="grupo_electrogeno",
        bus="tablero_general",
        kw=100,
        kv=0.4,
    )


def main():
    print("Construyendo modelo del hospital...")
    construir_modelo()

    print("\n--- Escenario 1: condición normal ---")
    server.ejecutar_flujo_potencia()
    normal = server.generar_diagrama_unifilar("diagrama_normal.html")
    print(f"Diagrama generado: {normal['archivo_generado']}")

    print("\n--- Escenario 2: contingencia N-1 ---")
    contingencia = server.simular_perdida_alimentador(
        "Line.alimentador_quirofanos",
        restaurar=False,
    )
    print(contingencia)
    cont = server.generar_diagrama_unifilar("diagrama_contingencia.html")
    print(f"Diagrama generado: {cont['archivo_generado']}")
    print(f"Buses desconectados: {cont['buses_desconectados']}")

    server.cerrar_elemento("Line.alimentador_quirofanos")
    print("\nModelo restaurado y resuelto.")


if __name__ == "__main__":
    main()
