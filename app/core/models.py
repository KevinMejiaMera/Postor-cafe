from django.db import models

class ConfiguracionSRI(models.Model):
    AMBIENTE_CHOICES = [
        ('1', 'Pruebas'),
        ('2', 'Producción'),
    ]
    
    api_url = models.URLField(
        default="https://factuexpress.fronteratech.ec/api/sri/documents/create_and_process_invoice_complete/",
        verbose_name="URL del Endpoint (Fronteratech)",
        help_text="URL completa del API de facturación"
    )
    api_token = models.CharField(max_length=255, blank=True, null=True, verbose_name="Token VSR o Usuario", help_text="Token de autenticación provisto por Fronteratech")
    ambiente = models.CharField(max_length=1, choices=AMBIENTE_CHOICES, default='1', verbose_name="Ambiente SRI")
    
    class Meta:
        verbose_name = "Configuración Facturación SRI"
        verbose_name_plural = "Configuración Facturación SRI"
        
    def __str__(self):
        return "Configuración Global SRI"
