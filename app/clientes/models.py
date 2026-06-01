
from django.db import models

class Cliente(models.Model):
    TIPO_IDENTIFICACION_CHOICES = [
        ('04', 'RUC'),
        ('05', 'Cédula'),
        ('06', 'Pasaporte'),
        ('07', 'Consumidor Final'),
        ('08', 'Identificación del Exterior'),
    ]

    # RUC o Cédula es único para no duplicar clientes
    tipo_identificacion = models.CharField(max_length=2, choices=TIPO_IDENTIFICACION_CHOICES, default='05', verbose_name="Tipo de Identificación SRI")
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