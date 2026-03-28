from django.db import models
from django.conf import settings

class SesionCaja(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    fecha_apertura = models.DateTimeField(auto_now_add=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    monto_inicial = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto Inicial en Caja")
    monto_final_sistema = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Total Ventas (Sistema)")
    monto_final_fisico = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Dinero en Mano")
    diferencia = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    estado = models.BooleanField(default=True, verbose_name="¿Caja Abierta?") # True = Abierta, False = Cerrada

class Gasto(models.Model):
    MODULO_CHOICES = [('restaurante', 'Restaurante'), ('hostal', 'Hostal')]
    descripcion = models.CharField(max_length=255, verbose_name="Descripción del Gasto")
    monto = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto Gastado")
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="Registrado por")
    modulo = models.CharField(max_length=20, choices=MODULO_CHOICES, default='restaurante')
    sesion_caja = models.ForeignKey(SesionCaja, on_delete=models.CASCADE, null=True, blank=True, related_name='gastos')
    sesion_caja_hostal = models.ForeignKey('hostal.SesionCajaHostal', on_delete=models.CASCADE, null=True, blank=True, related_name='gastos_hostal')

    def __str__(self):
        return f"{self.descripcion} - ${self.monto} ({self.modulo})"
