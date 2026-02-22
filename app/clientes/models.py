
from django.db import models

class Cliente(models.Model):
    # RUC o Cédula es único para no duplicar clientes
    cedula_o_ruc = models.CharField(max_length=13, unique=True, verbose_name="RUC/CI")
    nombres = models.CharField(max_length=200, verbose_name="Nombre Completo/Razón Social")
    email = models.EmailField(blank=True, null=True)
    direccion = models.CharField(max_length=200, blank=True, null=True, verbose_name="Dirección")
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombres} ({self.cedula_o_ruc})"

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"