from django.contrib import admin
from .models import TipoHabitacion, Habitacion, Huesped, Reserva

@admin.register(TipoHabitacion)
class TipoHabitacionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio_noche', 'capacidad_personas')

@admin.register(Habitacion)
class HabitacionAdmin(admin.ModelAdmin):
    list_display = ('numero', 'tipo', 'estado', 'esta_limpia', 'piso')
    list_filter = ('estado', 'tipo', 'esta_limpia')
    search_fields = ('numero',)

@admin.register(Huesped)
class HuespedAdmin(admin.ModelAdmin):
    list_display = ('nombre_completo', 'documento_identidad', 'telefono')
    search_fields = ('nombre_completo', 'documento_identidad')

@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ('id', 'huesped', 'habitacion', 'fecha_checkin', 'fecha_checkout', 'estado', 'precio_total')
    list_filter = ('estado', 'fecha_checkin')
    search_fields = ('huesped__nombre_completo', 'habitacion__numero')
