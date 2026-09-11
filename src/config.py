import os
import plotly.express as px

# Configuración de KoboToolbox API v2
DEFAULT_KOBO_BASE_URL = os.getenv("KOBO_BASE_URL", "https://kfm.asesoresencuesta.com/api/v2")
DEFAULT_KOBO_API_TOKEN = os.getenv("KOBO_API_TOKEN", "1489245d83fe3bc5860959d06d7e7582bfc88a8c")

# Configuración de la página Streamlit
PAGE_TITLE = "Registros no respuesta por control"
LAYOUT = "wide"

# Columnas para mostrar en la tabla detallada
COLS_TO_SHOW = ['encuestador', 'Tipo_Encuesta', 'id_vivienda', 'semana', 'control', 'nrolinea', 'estatusentrevista']

# Paleta de colores para gráficos
COLOR_MAP = {
    'Diligenciadas': '#2ecc71',
    'No Diligenciadas': '#ff7675'
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

# Mapeo de corrección para códigos de control erróneos ingresados en campo
CONTROL_REMAPS = {
    '06160010': '16060037',
    '6160010': '16060037',
}

# Mapeo de códigos de municipio a nombres oficiales (Estado Monagas)
MUNICIPIOS_MAP = {
    '1601': '1601 - Acosta',
    '1602': '1602 - Aguasay',
    '1603': '1603 - Bolívar',
    '1604': '1604 - Caripe',
    '1605': '1605 - Cedeño',
    '1606': '1606 - Ezequiel Zamora',
    '1607': '1607 - Libertador',
    '1608': '1608 - Maturín',
    '1609': '1609 - Piar',
    '1610': '1610 - Punceres',
    '1611': '1611 - Santa Bárbara',
    '1612': '1612 - Sotillo',
    '1613': '1613 - Uracoa',
    '1': '1601 - Acosta',
    '2': '1602 - Aguasay',
    '3': '1603 - Bolívar',
    '4': '1604 - Caripe',
    '5': '1605 - Cedeño',
    '6': '1606 - Ezequiel Zamora',
    '7': '1607 - Libertador',
    '8': '1608 - Maturín',
    '9': '1609 - Piar',
    '10': '1610 - Punceres',
    '11': '1611 - Santa Bárbara',
    '12': '1612 - Sotillo',
    '13': '1613 - Uracoa',
}
