# Documentación de Arquitectura

## 🏗️ Visión General
El sistema utiliza una arquitectura monolítica modular basada en **Streamlit** para la capa de presentación y **SQLite** para la persistencia de datos. El diseño sigue el patrón de separación de intereses (SoC), dividiendo claramente la interfaz de usuario (UI) de la lógica de negocio y el acceso a datos.

## 📐 Capas del Sistema

### 1. Capa de Presentación (UI) (`src/ui/`)
Esta capa maneja la interacción con el usuario y el renderizado de vistas.
*   **`main.py`**: Controlador principal. Gestiona la navegación (Sidebar), la selección de "Marca" (estado global) y el enrutamiento a las páginas.
*   **State Management (`src/ui/state_manager.py`)**: Módulo crítico que verifica que una marca esté seleccionada antes de permitir operaciones.
*   **Módulos de Página**:
    *   `ventas.py`: Interfaz de POS.
    *   `stock.py`: Gestión de inventario.
    *   `concesion.py`: Lógica compleja de consignación y movimientos entre depósitos.
    *   `facturacion.py`: Reportes y edición de estados de venta.

### 2. Lógica de Negocio y Servicios (`src/services/`)
Contiene las reglas de negocio y actúa como intermediario entre la UI y la base de datos.
*   **`sqlite_service.py`**: Servicio central (Core). Maneja el CRUD de Stock y Ventas. Implementa transacciones atómicas para asegurar que el stock y la venta se registren simultáneamente o fallen juntos.
*   **`concesion_service.py`**: Extensión para lógica de consignación. Maneja las tablas `concesionarios`, `concesion_stock`, y la lógica de "retorno de stock" o "venta de concesión".
*   **`cliente_service.py`**: Gestión simple de clientes.
*   **`reports.py`**: Agregación de datos pura (Pandas) para analíticas del Dashboard.

### 3. Capa de Datos (Data Layer)
*   **Motor**: SQLite (`ventas_veta.db`).
*   **Schema**:
    *   `stock`: Inventario maestro.
    *   `ventas` & `ventas_items`: Historial transaccional.
    *   `concesionarios` & `concesion_stock`: Inventario segregado por socio.
    *   `clientes`: Base de datos de contacto.

## 🔑 Concepto Clave: Arquitectura Multi-Marca
El sistema implementa "Multi-Tenancy lógico" mediante la columna discriminadora `marca` en todas las tablas principales.
*   **Segregación**: Cada consulta SQL en los servicios recibe el parámetro `marca` (inyectado desde la UI).
*   **Transparencia**: El usuario opera en un contexto (ej. "VETA") y el sistema filtra automáticamente, haciendo invisible la data de "VENETO".
*   **Flexibilidad**: Permite reportes consolidados (ej. Facturación Global) simplemente omitiendo el filtro `marca`.

## 🔄 Flujos Críticos

### Proceso de Venta
1.  **UI**: Usuario selecciona productos y cantidades.
2.  **Validación**: Se verifica `min_stock` y disponibilidad.
3.  **Transacción (`registrar_venta`)**:
    *   `BEGIN TRANSACTION`
    *   `UPDATE stock SET cantidad = cantidad - X` (Falla si stock < 0)
    *   `INSERT INTO ventas`
    *   `INSERT INTO ventas_items`
    *   `COMMIT`

### Proceso de Facturación (Corrección)
1.  **UI**: Usuario edita una cantidad en una venta pasada.
2.  **Servicio (`actualizar_cantidad_item_venta`)**:
    *   Calcula el delta (Nueva Cantidad - Vieja Cantidad).
    *   Resta/Suma el delta al `stock`.
    *   Actualiza el item de venta.
    *   Recalcula totales de la cabecera de venta.
