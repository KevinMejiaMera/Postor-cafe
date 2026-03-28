from django.urls import path
from . import views

app_name = 'caja'

urlpatterns = [
    path('gestion/', views.gestion_caja, name='gestion_caja'),
    path('gastos/', views.gestion_gastos, name='gestion_gastos'),
    path('gastos/restaurante/', views.gestion_gastos_restaurante, name='gestion_gastos_restaurante'),
    path('gastos/hostal/', views.gestion_gastos_hostal, name='gestion_gastos_hostal'),
]

