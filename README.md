# Sistema de Gestión de Ventas - VENTAS VETA (Multi-Marca)

Aplicación web desarrollada en Python con Streamlit para la gestión integral de inventario y ventas. Soporta arquitectura multi-marca (VETA / VENETO) con segregación lógica de datos.

## 🚀 Características Principales

*   **Gestión Multi-Marca**: Almacenamiento y gestión de datos separados para múltiples marcas desde una única instancia.
*   **Inventario**: CRUD completo de productos, control de stock mínimo y alertas.
*   **Ventas**: Punto de venta (POS) ágil con cálculo automático de totales, descuentos y control de stock en tiempo real.
*   **Consignación**: Módulo avanzado para socios/concesionarios con control de stock propio y liquidación de ventas.
*   **Facturación**: Panel consolidado para el seguimiento del estado de facturación (Pendiente/Facturado) validado con CUIT/CUIL.
*   **Dashboard**: Métricas KPI (MTD, YTD), tendencias de ingresos y análisis de productos top.

## 🛠️ Requisitos Técnicos

*   **Python**: 3.8 o superior.
*   **Base de Datos**: SQLite (Incluido por defecto, sin configuración externa).
*   **Librerías**: Listadas en `requirements.txt` (pandas, streamlit, pydantic, etc).

## 📦 Instalación y Ejecución

1.  **Clonar/Copiar el proyecto** a tu máquina local.
2.  **Instalar Dependencias**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Iniciar la Aplicación**:
    ```bash
    streamlit run main.py
    ```
4.  La aplicación se abrirá automáticamente en tu navegador predeterminado (o en `http://localhost:8501`).

## 📂 Estructura del Proyecto

*   `main.py`: Punto de entrada de la aplicación.
*   `src/`: Código fuente.
    *   `src/ui/`: Componentes visuales y páginas (Dashboard, Ventas, Stock, etc).
    *   `src/services/`: Lógica de negocio y acceso a datos (SQLite).
    *   `src/models.py`: Definiciones de tipos de datos (Pydantic).

## 🛡️ Seguridad y Datos

*   La base de datos se almacena localmente en `ventas_veta.db`.
*   Se recomienda realizar copias de seguridad de este archivo periódicamente.
