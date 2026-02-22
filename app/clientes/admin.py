
from django.contrib import admin
from .models import Cliente

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    # Campos que se verán en la lista de clientes
    list_display = ('nombres', 'cedula_o_ruc', 'email', 'telefono', 'created_at')
    
    # Campos por los que podrás buscar
    search_fields = ('nombres', 'cedula_o_ruc', 'email')
    
    # Filtros laterales (opcional, por fecha de creación)
    list_filter = ('created_at',)