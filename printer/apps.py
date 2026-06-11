from django.apps import AppConfig


class PrinterConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'printer'
    verbose_name = 'Sistema de Impresión'
    
    def ready(self):
        """
        Ejecutar código cuando Django inicia
        """
        # Aquí puedes importar signals si los necesitas en el futuro
        # import printer.signals
        pass