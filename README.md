# Control de Encuestadores INE - 2025 📊

## Descripción del Proyecto
Este proyecto es una aplicación web interactiva desarrollada con **Streamlit** para el monitoreo y control en tiempo real de los operativos de campo del **Instituto Nacional de Estadística (INE)** para el periodo 2025-2026.

Su objetivo principal es centralizar y visualizar los datos provenientes de las encuestas **EHM** y **ESCA**, permitiendo a los supervisores y analistas evaluar el rendimiento de los encuestadores, identificar cuellos de botella en la recolección de datos y analizar los motivos de "No Respuesta" de manera eficiente.

## Características Principales
*   **Panel de KPIs Globales**: Visualización instantánea de encuestas totales asignadas, efectivas, no respuestas y porcentaje de efectividad.
*   **Análisis de Rendimiento**: Gráficos comparativos por encuestador para medir la productividad individual.
*   **Desglose de No Respuestas**: Análisis detallado de los motivos por los cuales no se completaron las encuestas (viviendas desocupadas, rechazos, ausencias, etc.) mediante gráficos de distribución dinámicos.
*   **Filtros Inteligentes**: Capacidad de segmentar la información por:
    *   Tipo de Encuesta (EHM / ESCA).
    *   Semestre de ejecución.
    *   Encuestador específico.
*   **Integración de Datos**: Procesamiento automático de archivos Excel (`.xlsx`) con múltiples hojas, incluyendo limpieza de nombres y normalización de variables.

## Tecnologías Utilizadas
*   **Python**: Lenguaje principal.
*   **Streamlit**: Framework para la interfaz de usuario.
*   **Pandas**: Procesamiento y limpieza de datos.
*   **Plotly**: Gráficos interactivos y dinámicos.
*   **Openpyxl**: Motor para la lectura de archivos Excel.

## Estructura del Repositorio
*   `dashboard.py`: Archivo principal que ejecuta la aplicación.
*   `src/`: Carpeta de código fuente.
    *   `config.py`: Configuraciones globales, paletas de colores y mapeo de variables.
    *   `data_processor.py`: Lógica de carga, limpieza y transformación de datos.
*   `data/`: Carpeta (local) destinada a contener los archivos Excel de entrada (Ignorada en Git por seguridad).

## Instalación y Ejecución

1.  **Clonar el repositorio:**
    ```bash
    git clone https://github.com/Alexjhzg/no-respuestas-dashboard.git
    cd no-respuestas-dashboard
    ```

2.  **Crear un entorno virtual (opcional pero recomendado):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # En Windows: venv\Scripts\activate
    ```

3.  **Instalar dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Ejecutar la aplicación:**
    ```bash
    streamlit run dashboard.py
    ```
