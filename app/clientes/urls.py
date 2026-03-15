
from django.urls import path
from . import views

app_name = 'clientes'

urlpatterns = [
    #path('asignar/<int:pedido_id>/<int:cliente_id>/', views.asignar_cliente, name='asignar_cliente'),
    path('lista/', views.lista_clientes, name='lista'),
    path('buscar/', views.buscar_cliente, name='buscar'),
    path('crear/', views.crear_cliente_modal, name='modal_crear'),
    path('pos-crear-fields/', views.pos_crear_cliente_fields, name='pos_crear_fields'),
]