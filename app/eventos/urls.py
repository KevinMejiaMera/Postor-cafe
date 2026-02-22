from django.urls import path
from . import views

app_name = 'eventos'

urlpatterns = [
    path('dashboard/', views.dashboard_eventos, name='dashboard_eventos'),
    path('crear/', views.crear_evento, name='crear_evento'),
    path('simulador/<int:evento_id>/', views.simulador_evento, name='simulador_evento'),
    
    # Actions
    path('actualizar_datos/<int:evento_id>/', views.actualizar_evento_datos, name='actualizar_evento_datos'),
    
    # Menu
    path('agregar_plato/<int:evento_id>/', views.agregar_plato_evento, name='agregar_plato_evento'),
    path('eliminar_plato/<int:item_id>/', views.eliminar_plato_evento, name='eliminar_plato_evento'),
    
    # Menaje
    path('auto_calcular_menaje/<int:evento_id>/', views.auto_calcular_menaje, name='auto_calcular_menaje'),
    path('agregar_menaje/<int:evento_id>/', views.agregar_item_menaje, name='agregar_item_menaje'),
    path('eliminar_menaje/<int:item_id>/', views.eliminar_item_menaje, name='eliminar_item_menaje'),
    
    # Gastos
    path('agregar_gasto/<int:evento_id>/', views.agregar_gasto, name='agregar_gasto'),
    path('eliminar_gasto/<int:item_id>/', views.eliminar_gasto, name='eliminar_gasto'),
    
    # Ingresos
    path('agregar_ingreso/<int:evento_id>/', views.agregar_ingreso, name='agregar_ingreso'),
    path('eliminar_ingreso/<int:item_id>/', views.eliminar_ingreso, name='eliminar_ingreso'),

    # Legacy (se mantienen por si acaso, aunque redirijan o no se usen)
    path('agregar_extra/<int:evento_id>/', views.agregar_costo_extra, name='agregar_costo_extra'),
    path('eliminar_extra/<int:item_id>/', views.eliminar_costo_extra, name='eliminar_costo_extra'),
    
    # API
    path('api/eventos/', views.api_eventos, name='api_eventos'),
]
