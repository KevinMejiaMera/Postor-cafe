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

    def __str__(self):
        return f"Caja {self.usuario} - {self.fecha_apertura.strftime('%d/%m/%Y %H:%M')}"
