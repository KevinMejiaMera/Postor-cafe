
from django.urls import path
from . import views

app_name = 'pedidos'

urlpatterns = [
    path('mesa/<int:mesa_id>/', views.detalle_mesa, name='detalle_mesa'),
    path('agregar/<int:pedido_id>/<int:producto_id>/', views.agregar_producto, name='agregar_producto'),
    path('confirmar/<int:pedido_id>/', views.confirmar_pedido, name='confirmar_pedido'),
    path('pagar/<int:pedido_id>/', views.pagar_pedido, name='pagar_pedido'),
    path('cocina/', views.dashboard_cocina, name='dashboard_cocina'),
    path('cocina/terminar/<int:pedido_id>/', views.terminar_pedido, name='terminar_pedido'),
    path('modificar-cantidad/<int:item_id>/<str:accion>/', views.modificar_cantidad_item, name='modificar_cantidad'),
    path('cocina/actualizar/', views.actualizar_cocina, name='actualizar_cocina'),
    path('pedido/<int:pedido_id>/cobrar/', views.modal_cobrar, name='modal_cobrar'),
    path('pedido/<int:pedido_id>/pagar/', views.procesar_pago, name='procesar_pago'),
    path('pedido/<int:pedido_id>/comanda/', views.ver_comanda, name='ver_comanda'),
    path('factura/<int:factura_id>/ticket/', views.ver_ticket, name='ver_ticket'),
    path('', views.panel_mesas, name='panel_mesas'),
    
    
    path('productos/nuevo/', views.crear_producto, name='crear_producto'),
    path('productos/editar/<int:pk>/', views.editar_producto, name='editar_producto'),
    path('productos/eliminar/<int:pk>/', views.eliminar_producto, name='eliminar_producto'),
    path('productos/<int:producto_id>/receta/', views.gestion_receta, name='gestion_receta'),
    path('receta/eliminar/<int:receta_id>/', views.eliminar_ingrediente, name='eliminar_ingrediente'),
    path('check_notificaciones/', views.check_notificaciones, name='check_notificaciones'),
    # Notificación y Reporte
    path('notificacion/<int:pedido_id>/vista/', views.marcar_notificacion_vista, name='marcar_notificacion_vista'),
    path('reportes/tiempos/', views.reporte_tiempos_cocina, name='reporte_tiempos_cocina'),
    
    # Ingeniería de Menú
    path('productos/<int:producto_id>/ficha-tecnica/', views.ver_ficha_tecnica, name='ver_ficha_tecnica'),

    # Sub-recetas (Insumos)
    path('insumos/<int:insumo_id>/receta/', views.gestion_receta_insumo, name='gestion_receta_insumo'),
    path('insumos/receta/eliminar/<int:receta_id>/', views.eliminar_ingrediente_insumo, name='eliminar_ingrediente_insumo'),
    
    # API Agenda
    path('api/agenda/', views.api_pedidos_agenda, name='api_pedidos_agenda'),
    path('nuevo/agendado/', views.crear_pedido_agendado, name='crear_pedido_agendado'),
    path('editar/pedido/<int:pedido_id>/', views.editar_pedido_directo, name='editar_pedido_directo'),
]
