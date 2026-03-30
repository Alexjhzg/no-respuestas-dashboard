import sys
import os
import pandas as pd

# Añadir el directorio raíz al path para importar los módulos desde 'src'
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.append(root_dir)

from src.data_processor import get_kpis

def test_get_kpis():
    """
    Prueba básica de la función de cálculo de KPIs con datos sintéticos.
    """
    print("Ejecutando prueba: test_get_kpis...")
    
    data = {'entrevista': [1, 1, 0, 1, 0]} 
    df = pd.DataFrame(data)
    
    kpis = get_kpis(df)
    
    assert kpis['total_asignadas'] == 5
    assert kpis['encuestas_efectivas'] == 3
    assert kpis['no_respuestas'] == 2
    assert kpis['porcentaje_efectividad'] == 60.0
    
    print("✅ Prueba test_get_kpis completada exitosamente.")

if __name__ == "__main__":
    try:
        test_get_kpis()
        print("\n¡Todas las pruebas pasaron satisfactoriamente!")
    except AssertionError as e:
        print(f"\n❌ Falla en las pruebas: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        sys.exit(1)
