from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    path('insumo/nuevo/', views.crear_insumo, name='crear_insumo'),
    path('insumo/editar/<int:pk>/', views.editar_insumo, name='editar_insumo'),
    path('movimiento/nuevo/', views.registrar_movimiento, name='registrar_movimiento'),
    path('insumo/eliminar/<int:pk>/', views.eliminar_insumo, name='eliminar_insumo'),
]
