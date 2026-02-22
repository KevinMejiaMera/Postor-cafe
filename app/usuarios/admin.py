# 📁 usuarios/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, AuditLog

# Función auxiliar para obtener la IP del usuario
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

class CustomUserAdmin(UserAdmin):
    model = Usuario
    
    # 1. QUÉ VER EN LA LISTA
    list_display = ('username', 'email', 'rol', 'cedula', 'is_active')
    list_filter = ('rol', 'is_active')
    search_fields = ('username', 'email', 'cedula')

    # 2. PANTALLA DE EDICIÓN (Aquí SÍ mostramos todos tus campos personalizados)
    fieldsets = UserAdmin.fieldsets + (
        ('Información del Restaurante', {'fields': ('rol', 'cedula', 'telefono', 'direccion')}),
    )
    
    # 3. PANTALLA DE CREACIÓN (ADD USER)
    # Usamos la configuración original de Django (Solo Usuario y Pass) para evitar errores.
    add_fieldsets = UserAdmin.add_fieldsets

    # --- AUDITORÍA AUTOMÁTICA AL GUARDAR/EDITAR ---
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        
        # Determinamos si es creación o edición para el mensaje
        tipo_accion = "Modificación" if change else "Creación"
        detalle = f"{tipo_accion} de usuario: {obj.username} ({obj.get_rol_display()})"
        
        # Creamos el registro en el AuditLog
        AuditLog.objects.create(
            user=request.user, # El admin que hizo la acción
            ip_address=get_client_ip(request),
            action=detalle
        )

    # --- ACCIONES PERSONALIZADAS ---
    actions = ['desactivar_usuarios', 'activar_usuarios']

    @admin.action(description='Desactivar usuarios (Borrado Lógico)')
    def desactivar_usuarios(self, request, queryset):
        rows_updated = queryset.update(is_active=False)
        
        # Registramos la acción en el log para cada usuario desactivado
        for usuario in queryset:
             AuditLog.objects.create(
                user=request.user,
                ip_address=get_client_ip(request),
                action=f"Desactivación de usuario: {usuario.username}"
            )
            
        self.message_user(request, f"{rows_updated} usuario(s) fueron desactivados.")

    @admin.action(description='Reactivar usuarios')
    def activar_usuarios(self, request, queryset):
        rows_updated = queryset.update(is_active=True)
        
        # Registramos la acción en el log
        for usuario in queryset:
             AuditLog.objects.create(
                user=request.user,
                ip_address=get_client_ip(request),
                action=f"Reactivación de usuario: {usuario.username}"
            )

        self.message_user(request, f"{rows_updated} usuario(s) fueron reactivados.")

    # Prohibir el borrado real
    def has_delete_permission(self, request, obj=None):
        return False

# REGISTRO DE MODELOS
admin.site.register(Usuario, CustomUserAdmin)

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'ip_address', 'timestamp')
    readonly_fields = ('user', 'action', 'ip_address', 'timestamp')
    
    def has_delete_permission(self, request, obj=None):
        return False