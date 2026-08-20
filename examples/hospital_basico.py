"""
Ejemplo: red de distribución MT/BT de un hospital básico.

Este script llama directamente a las funciones de server.py (sin pasar por
MCP) para que puedas probar la lógica del modelo de forma aislada, o usarlo
como referencia de qué parámetros pasar a cada herramienta.

Modela:
  - Acometida en media tensión (13.2 kV)
  - Transformador de distribución 500 kVA (13.2 kV / 0.4 kV)
  - Tablero de quirófanos (carga crítica)
  - Tablero de iluminación general (carga no crítica)

Corre:
  - Flujo de potencia (voltajes por bus, pérdidas)
  - Contingencia N-1 sobre la línea de BT (simula pérdida del alimentador)

Uso:
    python3 examples/hospital_basico.py
"""

import sys
import os
import json

# Permite importar server.py desde la raíz del repo al correr este
# script directamente desde la carpeta examples/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import server


def main():
    print("=" * 60)
    print("CASO DE ESTUDIO: Hospital básico - Red MT/BT")
    print("=" * 60)

    print("\n--- 1. Creación del circuito ---")
    print(server.crear_circuito("hospital_central", kv_base=13.2))

    print("\n--- 2. Topología ---")
    print(
        server.agregar_transformador(
            nombre="trafo_principal",
            bus_primario="sourcebus",
            bus_secundario="tablero_general",
            kva=500,
            kv_primario=13.2,
            kv_secundario=0.4,
        )
    )
    print(
        server.agregar_linea(
            nombre="alimentador_quirofanos",
            bus1="tablero_general",
            bus2="tablero_quirofanos",
            longitud_km=0.05,
            r1_ohm_km=0.5,
            x1_ohm_km=0.3,
        )
    )

    print("\n--- 3. Cargas ---")
    print(
        server.agregar_carga(
            nombre="quirofanos",
            bus="tablero_quirofanos",
            kw=50,
            kvar=20,
            critica=True,
        )
    )
    print(
        server.agregar_carga(
            nombre="iluminacion_general",
            bus="tablero_general",
            kw=20,
            kvar=5,
        )
    )

    print("\n--- 4. Generador de respaldo (grupo electrógeno) ---")
    print(
        server.agregar_generador_respaldo(
            nombre="grupo_electrogeno",
            bus="tablero_general",
            kw=100,
            kv=0.4,
        )
    )

    print("\n--- 5. Flujo de potencia (condición normal) ---")
    resultado_flujo = server.ejecutar_flujo_potencia()
    print(json.dumps(resultado_flujo, indent=2, ensure_ascii=False))

    print("\n--- 6. Análisis de contingencia N-1 ---")
    print("Simulando pérdida del alimentador a quirófanos...")
    resultado_contingencia = server.simular_perdida_alimentador(
        "Line.alimentador_quirofanos"
    )
    print(json.dumps(resultado_contingencia, indent=2, ensure_ascii=False))

    print("\n--- 7. Inventario final del modelo ---")
    print(json.dumps(server.listar_elementos(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
