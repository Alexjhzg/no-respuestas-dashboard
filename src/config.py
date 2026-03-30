import os
import plotly.express as px

# Configuración de archivos
DATA_FILES = {
    "EHM": os.path.join("data", "EHM 2025-2026 ENCUESTADORES  INE.xlsx"),
    "ESCA": os.path.join("data", "ESCA 2025-2026 ENCUESTADORES  INE.xlsx")
}

# Configuración de la página Streamlit
PAGE_TITLE = "📊 Control de Encuestadores INE - 2025"
LAYOUT = "wide"

# Columnas para mostrar en la tabla detallada
COLS_TO_SHOW = ['encuestador', 'Tipo_Encuesta', 'id_vivienda', 'semana', 'control', 'nrolinea', 'estatusentrevista']

# Paleta de colores para gráficos
COLOR_MAP = {
    'Efectivas': '#2ecc71',
    'No Respuestas': '#ff7675'
}
# Secuencia de colores variada para otros gráficos
COLOR_SEQUENCE = px.colors.qualitative.Prism

# Mapeo de siglas a nombres completos para estatus de entrevista
STATUS_MAPPING = {
    'DE': 'Demolida',
    'ML': 'Mal Listado',
    'NP': 'Negocio Permanente',
    'IU': 'Inadecuada para el Uso',
    'NE': 'No Existe',
    'OA': 'Ocupantes Ausentes',
    'CO': 'Construcción',
    'VO': 'Vivienda Ocasional',
    'VD': 'Vivienda Desocupada',
    'IC': 'Informante No Calificado',
    'UV': 'Uso Vacacional',
    'RZ': 'Rechazada',
    'TN': 'Temporalmente en Negocio',
    'OE': 'Otro (Especifique)',
    'TE': 'Totalmente Encuestada',
    'AT': 'Ausente Temporalmente',
    'SL': 'Sin Listar',
    'NT': 'No Existe Número Telefónico',
    'NO': 'No Atiende el Teléfono',
    'IN': 'Incompleta',
    'TA': 'Actualizada y No Seleccionada',
    'OT': 'Otra Condición',
    'OS': 'Otra Situación',
    'PE': 'Pendiente',
    'SE': 'Sin Entrevista'
}
