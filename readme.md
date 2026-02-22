# 🍽️ Sistema de Gestión de Restaurante "Postor Cafe San Pedro de Huaca"

Sistema integral web desarrollado en **Django** para la administración operativa y gerencial de un restaurante. Incluye control de inventario, punto de venta (POS) para meseros, monitor de cocina (KDS) y dashboard gerencial con reportes.

---

## 🚀 Características Principales

### 🔐 1. Módulo de Seguridad y Usuarios
* **Roles Definidos:** Administrador, Gerente, Mesero y Cocinero.
* **Login Seguro:** Acceso mediante Usuario o Correo Electrónico.
* **Protección:** Bloqueo de cuenta tras 5 intentos fallidos (Django Axes) y cierre de sesión por inactividad.
* **Auditoría:** Registro automático (Logs) de todas las acciones críticas (quién hizo qué y cuándo).

### 🍔 2. Módulo de Inventario y Costos
* **Gestión de Insumos:** Control de stock de ingredientes (Pan, Carne, etc.).
* **Recetas:** Enlace entre Productos de venta e Insumos.
* **Costeo Automático:** Cálculo del costo real de cada plato basado en sus ingredientes.
* **Kardex:** Registro histórico de entradas y salidas.
* **Descarga Automática:** Al vender un plato, se descuentan los ingredientes del inventario automáticamente.

### 📱 3. Módulo de Pedidos (Mesero)
* **Mapa de Mesas:** Visualización gráfica del estado (Libre/Ocupada).
* **Toma de Pedidos:** Interfaz ágil para agregar productos.
* **Buscador de Clientes (HTMX):** Búsqueda en tiempo real de clientes por Cédula o Nombre para facturación.
* **Flujo de Estados:** Borrador -> Confirmado (Cocina) -> Pagado -> Mesa Libre.

### 👨‍🍳 4. Módulo de Cocina (KDS)
* **Monitor en Tiempo Real:** Los pedidos confirmados aparecen instantáneamente.
* **Gestión de Despacho:** Los cocineros marcan los platos como "Listos".

### 📊 5. Módulo de Gerencia
* **Dashboard Ejecutivo:** Métricas clave (Ventas del día, Usuarios activos).
* **Reportes:** Exportación de historial de ventas a Excel (CSV).
* **Gestión de Personal:** Alta y baja de empleados con borrado lógico (desactivación).

---

## 🛠️ Tecnologías Utilizadas

* **Backend:** Python, Django 5.
* **Base de Datos:** PostgreSQL.
* **Frontend:** HTML5, CSS3, JavaScript (Vanilla).
* **Interactividad:** HTMX (para búsquedas y actualizaciones parciales).
* **Librerías Clave:** `django-jazzmin` (Admin), `django-axes` (Seguridad), `psycopg2` (Postgres).

---

## ⚙️ Guía de Instalación (Para Desarrolladores)

Sigue estos pasos para levantar el proyecto en tu máquina local.

### 1. Requisitos Previos
* Tener instalado **Python 3.10+**.
* Tener instalado **PostgreSQL** y **pgAdmin 4**.
* Tener instalado **Git**.

### 2. Clonar el Repositorio
```bash
git clone [https://github.com/jordanrevelo214-creator/Restaurante-Software.git](https://github.com/jordanrevelo214-creator/Restaurante-Software.git)
cd postor-cafe

cambio minimo en read.md 