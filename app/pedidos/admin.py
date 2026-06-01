
from django.contrib import admin
from .models import Mesa, Producto, Pedido, DetallePedido, CategoriaProducto, VarianteProducto, Factura
from inventario.models import Receta 

@admin.register(CategoriaProducto)
class CategoriaProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'slug')
    prepopulated_fields = {'slug': ('nombre',)}

# --- CONFIGURACIÓN PARA VER RECETAS DENTRO DEL PRODUCTO ---
class RecetaInline(admin.TabularInline):
    model = Receta
    extra = 1
    autocomplete_fields = ['insumo'] 

class VarianteProductoInline(admin.TabularInline):
    model = VarianteProducto
    extra = 1

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    # 👇 AQUÍ ESTÁ LA COLUMNA 'ver_costo'
    list_display = ('nombre', 'precio', 'ver_costo', 'stock', 'disponible')
    search_fields = ('nombre',)
    
    # 👇 ESTO PONE LAS FILAS ADENTRO DEL PRODUCTO
    inlines = [VarianteProductoInline, RecetaInline]

    # Función que calcula el costo visualmente
    def ver_costo(self, obj):
        return f"${obj.costo_elaboracion:.2f}"
    ver_costo.short_description = "Costo Real"

# --- CONFIGURACIÓN DE MESAS Y PEDIDOS (Ya la tenías) ---
@admin.register(Mesa)
class MesaAdmin(admin.ModelAdmin):
    list_display = ('numero', 'capacidad', 'estado')
    ordering = ('numero',)

class DetallePedidoInline(admin.TabularInline):
    model = DetallePedido
    fields = ('producto', 'variante', 'cantidad', 'precio_unitario', 'subtotal')
    readonly_fields = ('subtotal',)
    extra = 0

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'mesa', 'mesero', 'estado', 'total')
    list_filter = ('estado',)
    inlines = [DetallePedidoInline]

@admin.register(VarianteProducto)
class VarianteProductoAdmin(admin.ModelAdmin):
    list_display = ('producto', 'nombre', 'precio', 'disponible')
    list_filter = ('producto', 'disponible')
    search_fields = ('nombre', 'producto__nombre')

# --- HISTORIAL DE FACTURAS ---
@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'origen', 'total', 'estado_sri', 'secuencial', 'fecha_emision')
    list_filter = ('estado_sri', 'origen', 'fecha_emision')
    search_fields = ('secuencial', 'clave_acceso', 'razon_social', 'ruc_ci')
    readonly_fields = ('clave_acceso', 'estado_sri', 'fecha_autorizacion', 'secuencial')