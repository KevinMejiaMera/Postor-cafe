from django.contrib import admin
from .models import ConfiguracionSRI

@admin.register(ConfiguracionSRI)
class ConfiguracionSRIAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'ambiente', 'api_url')
    
    def has_add_permission(self, request):
        # Permitir agregar solo si no existe ninguna configuración
        if ConfiguracionSRI.objects.exists():
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        return False
