from django.contrib import admin
from .models import Evento, DetalleMenu, CategoriaMenaje, Menaje, ItemMenajeEvento, GastoEvento, IngresoEvento

class DetalleMenuInline(admin.TabularInline):
    model = DetalleMenu
    extra = 1

class ItemMenajeEventoInline(admin.TabularInline):
    model = ItemMenajeEvento
    extra = 1

class GastoEventoInline(admin.TabularInline):
    model = GastoEvento
    extra = 1

class IngresoEventoInline(admin.TabularInline):
    model = IngresoEvento
    extra = 1

@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'fecha_evento', 'estado', 'personas', 'costo_total_evento', 'ganancia')
    list_filter = ('estado', 'fecha_evento')
    inlines = [DetalleMenuInline, ItemMenajeEventoInline, GastoEventoInline, IngresoEventoInline]

@admin.register(CategoriaMenaje)
class CategoriaMenajeAdmin(admin.ModelAdmin):
    list_display = ('nombre',)

@admin.register(Menaje)
class MenajeAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'costo_alquiler', 'costo_reposicion')
    list_filter = ('categoria',)
