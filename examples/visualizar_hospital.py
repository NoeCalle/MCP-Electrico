"""
Ejemplo: visualización del circuito hospitalario en dos escenarios.

Reutiliza el mismo modelo de examples/hospital_basico.py, pero en vez de
solo imprimir resultados en texto, genera dos diagramas HTML interactivos:

  - diagrama_normal.html       : ambos alimentadores energizados
  - diagrama_contingencia.html : alimentador a quirófanos abierto (N-1)

Abre los archivos generados en tu navegador. Cada bus se colorea según su
voltaje en por-unidad (verde: normal, amarillo: marginal, rojo: fuera de
rango o sin tensión), y al pasar el mouse sobre un bus o una línea se
muestra el detalle.

Uso:
    python3 examples/visualizar_hospital.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import server
import opendssdirect as dss


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
        nombre="quirofanos", bus="tablero_quirofanos", kw=50, kvar=20, critica=True
    )
    server.agregar_carga(nombre="iluminacion_general", bus="tablero_general", kw=20, kvar=5)
    server.agregar_generador_respaldo(
        nombre="grupo_electrogeno", bus="tablero_general", kw=100, kv=0.4
    )


def main():
    print("Construyendo modelo del hospital...")
    construir_modelo()

    print("\n--- Escenario 1: condición normal ---")
    server.ejecutar_flujo_potencia()
    resultado = server.generar_diagrama_unifilar("diagrama_normal.html")
    print(f"Diagrama generado: {resultado['archivo_generado']}")
    print(f"  Buses: {resultado['buses_dibujados']}, Conexiones: {resultado['conexiones_dibujadas']}")

    print("\n--- Escenario 2: contingencia N-1 (alimentador a quirófanos abierto) ---")
    dss.run_command("Open Line.alimentador_quirofanos term=1")
    dss.run_command("Solve")
    resultado_cont = server.generar_diagrama_unifilar("diagrama_contingencia.html")
    print(f"Diagrama generado: {resultado_cont['archivo_generado']}")
    print("  (el bus tablero_quirofanos debería verse en rojo, sin tensión)")

    # Restaurar el elemento para dejar el modelo en un estado limpio
    dss.run_command("Close Line.alimentador_quirofanos term=1")

    print("\nListo. Abre diagrama_normal.html y diagrama_contingencia.html en tu navegador.")


if __name__ == "__main__":
    main()
