from django.urls import path
from . import views

app_name = 'hostal'

urlpatterns = [
    path('dashboard/', views.dashboard_hostal, name='dashboard_hostal'),
    path('crear-habitacion/', views.crear_habitacion, name='crear_habitacion'),
    path('procesar-checkin/', views.procesar_checkin, name='procesar_checkin'),
    path('reservas/', views.calendario_reservas, name='calendario_reservas'),
    path('nueva-reserva/', views.crear_reserva, name='crear_reserva'),
    path('reservas/cancelar/<int:reserva_id>/', views.cancelar_reserva, name='cancelar_reserva'),
    path('procesar-checkout/<int:habitacion_id>/', views.realizar_checkout, name='realizar_checkout'),
    path('finalizar-limpieza/<int:habitacion_id>/', views.finalizar_limpieza, name='finalizar_limpieza'),
    path('finanzas/', views.finanzas_hostal, name='finanzas_hostal'),
    path('habitaciones/', views.gestion_habitaciones, name='gestion_habitaciones'),
]
