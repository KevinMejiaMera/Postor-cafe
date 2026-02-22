
from django.urls import path
from . import views

app_name = 'usuarios'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/mesero/', views.dashboard_mesero, name='dashboard_mesero'),
    path('dashboard/gerente/', views.dashboard_gerente, name='dashboard_gerente'),
    path('dashboard/gerente/personal/', views.lista_usuarios, name='lista_usuarios'),
    path('dashboard/gerente/personal/nuevo/', views.crear_usuario, name='crear_usuario'),
    path('dashboard/gerente/personal/editar/<int:usuario_id>/', views.editar_usuario, name='editar_usuario'),
    path('dashboard/gerente/menu/', views.gestion_menu, name='gestion_menu'),
    path('dashboard/gerente/reportes/', views.reportes_ventas, name='reportes_ventas'),
    path('dashboard/gerente/inventario/', views.gestion_inventario, name='gestion_inventario'),
    path('dashboard/gerente/agenda/', views.agenda_pedidos, name='agenda_pedidos'),

    # Rutas para password reset
    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset-confirm/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
]
