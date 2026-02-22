

from django.contrib import admin
from .models import Proveedor, Insumo, MovimientoKardex, Receta

# Registramos el Insumo con la capacidad de BÚSQUEDA
@admin.register(Insumo)
class InsumoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'unidad_medida', 'stock_actual', 'costo_unitario')
    # 👇 ESTA ES LA LÍNEA QUE FALTA PARA ARREGLAR EL ERROR 👇
    search_fields = ['nombre'] 

admin.site.register(Proveedor)
admin.site.register(MovimientoKardex)
admin.site.register(Receta)