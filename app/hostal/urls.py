from django.urls import path
from . import views

app_name = 'hostal'

urlpatterns = [
    path('dashboard/', views.dashboard_hostal, name='dashboard_hostal'),
    path('crear-habitacion/', views.crear_habitacion, name='crear_habitacion'),
    path('crear-tipo-habitacion/', views.crear_tipo_habitacion, name='crear_tipo_habitacion'),
    path('modal-nueva-reserva/', views.modal_nueva_reserva, name='modal_nueva_reserva'),
    path('procesar-checkin/', views.procesar_checkin, name='procesar_checkin'),
    path('reservas/', views.calendario_reservas, name='calendario_reservas'),
    path('nueva-reserva/', views.crear_reserva, name='crear_reserva'),
    path('reservas/cancelar/<int:reserva_id>/', views.cancelar_reserva, name='cancelar_reserva'),
    path('procesar-checkout/<int:habitacion_id>/', views.realizar_checkout, name='realizar_checkout'),
    path('finalizar-limpieza/<int:habitacion_id>/', views.finalizar_limpieza, name='finalizar_limpieza'),
    path('finanzas/', views.finanzas_hostal, name='finanzas_hostal'),
    path('habitaciones/', views.gestion_habitaciones, name='gestion_habitaciones'),
    path('caja/', views.caja_hostal, name='caja_hostal'),
    path('reportes/', views.reportes_hostal, name='reportes_hostal'),
    # Gestión de Reservas
    path('reservas/detalle/<int:reserva_id>/', views.detalle_reserva_modal, name='detalle_reserva_modal'),
    path('reservas/editar/<int:reserva_id>/', views.editar_reserva_modal, name='editar_reserva_modal'),
    path('reservas/actualizar/<int:reserva_id>/', views.actualizar_reserva, name='actualizar_reserva'),
    path('reservas/eliminar/<int:reserva_id>/', views.eliminar_reserva, name='eliminar_reserva'),
    path('caja/detalle/<int:session_id>/', views.detalle_caja_hostal_modal, name='detalle_caja_hostal_modal'),
    path('caja/editar/<int:session_id>/', views.editar_caja_hostal_modal, name='editar_caja_hostal_modal'),
    path('caja/eliminar/<int:session_id>/', views.eliminar_caja_hostal, name='eliminar_caja_hostal'),
    path('caja/unificar/', views.unificar_cajas_hostal, name='unificar_cajas_hostal'),
]

