
from django.contrib import admin
from .models import Mesa, Producto, Pedido, DetallePedido
from inventario.models import Receta 

# --- CONFIGURACIÓN PARA VER RECETAS DENTRO DEL PRODUCTO ---
class RecetaInline(admin.TabularInline):
    model = Receta
    extra = 1
    autocomplete_fields = ['insumo'] 

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    # 👇 AQUÍ ESTÁ LA COLUMNA 'ver_costo'
    list_display = ('nombre', 'precio', 'ver_costo', 'stock', 'disponible')
    search_fields = ('nombre',)
    
    # 👇 ESTO PONE LAS FILAS ADENTRO DEL PRODUCTO
    inlines = [RecetaInline]

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
    extra = 0

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'mesa', 'mesero', 'estado', 'total')
    list_filter = ('estado',)
    inlines = [DetallePedidoInline]