from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


class Printer(models.Model):
    """Impresoras configuradas en el sistema"""
    PRINTER_TYPES = [
        ('thermal', 'Térmica (Tickets)'),
        ('laser', 'Láser (Facturas)'),
        ('matrix', 'Matriz de Puntos'),
    ]
    
    CONNECTION_TYPES = [
        ('usb', 'USB'),
        ('network', 'Red/IP'),
        ('bluetooth', 'Bluetooth'),
        ('serial', 'Serial/COM'),
        ('rawbt', 'Inalámbrica (App RawBT)'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, verbose_name='Nombre')
    printer_type = models.CharField(
        max_length=20,
        choices=PRINTER_TYPES,
        default='thermal',
        verbose_name='Tipo de Impresora'
    )
    
    # Conexión
    connection_type = models.CharField(
        max_length=20,
        choices=CONNECTION_TYPES,
        default='usb',
        verbose_name='Tipo de Conexión'
    )
    
    connection_string = models.CharField(
        max_length=255,
        verbose_name='Cadena de Conexión',
        help_text='USB: /dev/usb/lp0 | Red: 192.168.1.100 | COM: COM1'
    )
    
    port = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(65535)],
        verbose_name='Puerto',
        help_text='Puerto de red (ej: 9100 para impresoras ESC/POS)'
    )
    
    # Configuración
    paper_width = models.IntegerField(
        default=80,
        validators=[MinValueValidator(40), MaxValueValidator(210)],
        verbose_name='Ancho de Papel (mm)',
        help_text='58mm o 80mm típicamente'
    )
    
    characters_per_line = models.IntegerField(
        default=42,
        validators=[MinValueValidator(20), MaxValueValidator(80)],
        verbose_name='Caracteres por Línea'
    )
    
    # Control de caja registradora
    has_cash_drawer = models.BooleanField(
        default=True,
        verbose_name='Tiene Caja Registradora',
        help_text='Si la impresora tiene caja de dinero conectada'
    )
    
    cash_drawer_pin = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        verbose_name='Pin de Caja',
        help_text='0 = Pin 2, 1 = Pin 5'
    )
    
    cash_drawer_on_time = models.IntegerField(
        default=100,
        validators=[MinValueValidator(1), MaxValueValidator(500)],
        verbose_name='Tiempo ON (ms)',
        help_text='Tiempo que el pulso está activo'
    )
    
    cash_drawer_off_time = models.IntegerField(
        default=100,
        validators=[MinValueValidator(1), MaxValueValidator(500)],
        verbose_name='Tiempo OFF (ms)',
        help_text='Tiempo que el pulso está inactivo'
    )
    
    # Estado
    is_active = models.BooleanField(default=True, verbose_name='Activa')
    is_default = models.BooleanField(default=False, verbose_name='Impresora por Defecto')
    
    # Configuración adicional (JSON)
    config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Configuración Adicional',
        help_text='Configuración específica del driver'
    )
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Impresora'
        verbose_name_plural = 'Impresoras'
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active', 'is_default']),
        ]
    
    def __str__(self):
        return f'{self.name} ({self.get_printer_type_display()})'
    
    def clean(self):
        """Validación a nivel de modelo"""
        from django.core.exceptions import ValidationError
        
        if self.connection_type == 'network' and not self.port:
            raise ValidationError({
                'port': 'El puerto es requerido para impresoras de red'
            })
    
    def save(self, *args, **kwargs):
        # Solo puede haber una impresora por defecto
        if self.is_default:
            Printer.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
    
    @classmethod
    def get_default(cls):
        """Obtiene la impresora por defecto"""
        return cls.objects.filter(is_default=True, is_active=True).first()


class PrintTemplate(models.Model):
    """Plantillas de impresión"""
    TEMPLATE_TYPES = [
        ('receipt', 'Ticket de Venta'),
        ('invoice', 'Factura'),
        ('order_kitchen', 'Orden de Cocina'),
        ('order_bar', 'Orden de Bar'),
        ('daily_report', 'Reporte Diario'),
        ('cash_report', 'Reporte de Caja'),
        ('refund', 'Reembolso'),
        ('custom', 'Personalizado'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name='Nombre')
    template_type = models.CharField(
        max_length=20,
        choices=TEMPLATE_TYPES,
        verbose_name='Tipo de Plantilla'
    )
    
    # Contenido de la plantilla (puede ser Jinja2, HTML, o formato específico)
    content = models.TextField(
        verbose_name='Contenido de la Plantilla',
        help_text='Plantilla con variables como {{order_number}}, {{total}}, etc.'
    )
    
    # Configuración de impresión
    print_logo = models.BooleanField(default=True, verbose_name='Imprimir Logo')
    print_qr = models.BooleanField(default=False, verbose_name='Imprimir QR')
    
    auto_cut = models.BooleanField(
        default=True,
        verbose_name='Corte Automático',
        help_text='Cortar papel automáticamente después de imprimir'
    )
    
    copies = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name='Número de Copias'
    )
    
    # Estado
    is_active = models.BooleanField(default=True, verbose_name='Activa')
    is_default = models.BooleanField(
        default=False,
        verbose_name='Plantilla por Defecto',
        help_text='Plantilla por defecto para este tipo'
    )
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Plantilla de Impresión'
        verbose_name_plural = 'Plantillas de Impresión'
        ordering = ['template_type', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['template_type'],
                condition=models.Q(is_default=True),
                name='unique_default_template_per_type'
            )
        ]
        indexes = [
            models.Index(fields=['template_type', 'is_active']),
        ]
    
    def __str__(self):
        return f'{self.name} ({self.get_template_type_display()})'
    
    def save(self, *args, **kwargs):
        # Solo puede haber una plantilla por defecto por tipo
        if self.is_default:
            PrintTemplate.objects.filter(
                template_type=self.template_type,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class PrintJob(models.Model):
    """Trabajos de impresión (historial)"""
    JOB_STATUS = [
        ('pending', 'Pendiente'),
        ('printing', 'Imprimiendo'),
        ('completed', 'Completado'),
        ('failed', 'Fallido'),
        ('cancelled', 'Cancelado'),
    ]
    
    DOCUMENT_TYPES = [
        ('receipt', 'Ticket'),
        ('invoice', 'Factura'),
        ('order', 'Orden'),
        ('report', 'Reporte'),
        ('other', 'Otro'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # ✅ CORREGIDO: Aumentado a 35 caracteres
    job_number = models.CharField(
        max_length=35,
        unique=True,
        verbose_name='Número de Trabajo',
        db_index=True,
        editable=False
    )
    
    # Impresora utilizada
    printer = models.ForeignKey(
        Printer,
        on_delete=models.PROTECT,
        related_name='print_jobs',
        verbose_name='Impresora'
    )
    
    # Plantilla utilizada
    template = models.ForeignKey(
        PrintTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='print_jobs',
        verbose_name='Plantilla'
    )
    
    # Tipo de documento
    document_type = models.CharField(
        max_length=20,
        choices=DOCUMENT_TYPES,
        verbose_name='Tipo de Documento'
    )
    
    # Referencia genérica para relacionar con otros modelos
    related_model = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Modelo Relacionado',
        help_text='Nombre del modelo relacionado (ej: Order, Payment)'
    )
    related_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='ID Relacionado',
        help_text='ID del objeto relacionado'
    )
    
    # Contenido a imprimir (ya renderizado)
    content = models.TextField(verbose_name='Contenido')
    
    # Datos adicionales (JSON)
    data = models.JSONField(
        default=dict,
        verbose_name='Datos',
        help_text='Datos usados para generar el contenido'
    )
    
    # Control de caja registradora
    open_cash_drawer = models.BooleanField(
        default=False,
        verbose_name='Abrir Caja',
        help_text='Si se debe abrir la caja registradora al imprimir'
    )
    
    cash_drawer_opened = models.BooleanField(
        default=False,
        verbose_name='Caja Abierta',
        help_text='Si la caja fue abierta exitosamente'
    )
    
    # Estado
    status = models.CharField(
        max_length=20,
        choices=JOB_STATUS,
        default='pending',
        verbose_name='Estado',
        db_index=True
    )
    
    # Número de copias
    copies = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name='Copias'
    )
    
    # Error si falla
    error_message = models.TextField(
        blank=True,
        verbose_name='Mensaje de Error'
    )
    
    # Auditoría
    created_by = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Creado por'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Creado', db_index=True)
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='Iniciado')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Completado')
    
    class Meta:
        verbose_name = 'Trabajo de Impresión'
        verbose_name_plural = 'Trabajos de Impresión'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['printer', 'status']),
            models.Index(fields=['created_at', 'status']),
            models.Index(fields=['document_type', 'created_at']),
        ]
    
    def __str__(self):
        return f'Job #{self.job_number} - {self.get_document_type_display()}'
    
    def save(self, *args, **kwargs):
        # Generar número de trabajo si no existe
        if not self.job_number:
            self.job_number = self.generate_job_number()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_job_number():
        """Genera un número de trabajo único"""
        from datetime import datetime
        import random
        
        # Formato: PRINT-YYMMDDHHMMSS-XXXX (25 chars)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')  # 14 chars
        random_suffix = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=4))  # 4 chars
        
        job_number = f'PRINT-{timestamp}-{random_suffix}'  # PRINT- (6) + 14 + - (1) + 4 = 25 chars
        
        # Verificar unicidad (por si acaso)
        while PrintJob.objects.filter(job_number=job_number).exists():
            random_suffix = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=4))
            job_number = f'PRINT-{timestamp}-{random_suffix}'
        
        return job_number
    
    def mark_as_printing(self):
        """Marca el trabajo como en impresión"""
        if self.status == 'pending':
            self.status = 'printing'
            self.started_at = timezone.now()
            self.save(update_fields=['status', 'started_at'])
            return True
        return False
    
    def mark_as_completed(self):
        """Marca el trabajo como completado"""
        if self.status == 'printing':
            self.status = 'completed'
            self.completed_at = timezone.now()
            self.save(update_fields=['status', 'completed_at'])
            return True
        return False
    
    def mark_as_failed(self, error_message=''):
        """Marca el trabajo como fallido"""
        self.status = 'failed'
        self.error_message = error_message
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'error_message', 'completed_at'])
        return True


class CashDrawerEvent(models.Model):
    """Historial de aperturas de caja registradora"""
    EVENT_TYPES = [
        ('print', 'Apertura por Impresión'),
        ('manual', 'Apertura Manual'),
        ('register_open', 'Apertura de Turno'),
        ('register_close', 'Cierre de Turno'),
        ('test', 'Prueba'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Impresora que abrió la caja
    printer = models.ForeignKey(
        Printer,
        on_delete=models.PROTECT,
        related_name='cash_drawer_events',
        verbose_name='Impresora'
    )
    
    # Trabajo de impresión asociado (si aplica)
    print_job = models.ForeignKey(
        PrintJob,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cash_drawer_events',
        verbose_name='Trabajo de Impresión'
    )
    
    # Tipo de evento
    event_type = models.CharField(
        max_length=20,
        choices=EVENT_TYPES,
        default='print',
        verbose_name='Tipo de Evento'
    )
    
    # Éxito
    success = models.BooleanField(default=True, verbose_name='Exitoso')
    
    # Notas
    notes = models.TextField(blank=True, verbose_name='Notas')
    
    # Auditoría
    triggered_by = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Activado por'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        verbose_name = 'Evento de Caja'
        verbose_name_plural = 'Eventos de Caja'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['printer', 'created_at']),
            models.Index(fields=['event_type', 'created_at']),
        ]
    
    def __str__(self):
        return f'{self.get_event_type_display()} - {self.created_at.strftime("%Y-%m-%d %H:%M")}'


class PrinterSettings(models.Model):
    """Configuración global del sistema de impresión (Singleton)"""
    id = models.AutoField(primary_key=True)
    
    # Logo de la empresa (imagen en base64 o ruta)
    company_logo = models.TextField(
        blank=True,
        verbose_name='Logo de la Empresa',
        help_text='Imagen en base64 o ruta al archivo. Si está vacío, usa COMPANY_CONFIG["logo"] de settings.py'
    )
    
    # Información de la empresa
    company_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Nombre de la Empresa',
        help_text='Si está vacío, usa COMPANY_CONFIG["name"] de settings.py'
    )
    
    company_address = models.TextField(
        blank=True,
        verbose_name='Dirección',
        help_text='Si está vacío, usa COMPANY_CONFIG["address"] de settings.py'
    )
    
    company_phone = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Teléfono',
        help_text='Si está vacío, usa COMPANY_CONFIG["phone"] de settings.py'
    )
    
    company_email = models.EmailField(
        blank=True,
        verbose_name='Email',
        help_text='Si está vacío, usa COMPANY_CONFIG["email"] de settings.py'
    )
    
    company_website = models.URLField(
        blank=True,
        verbose_name='Sitio Web',
        help_text='Si está vacío, usa COMPANY_CONFIG["website"] de settings.py'
    )
    
    # Información fiscal
    tax_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='RUC/NIT/RFC',
        help_text='Si está vacío, usa COMPANY_CONFIG["tax_id"] de settings.py'
    )
    
    # Mensajes personalizados
    receipt_header = models.TextField(
        blank=True,
        verbose_name='Encabezado de Ticket',
        help_text='Si está vacío, usa PRINTING_CONFIG["receipt_header"] de settings.py'
    )
    
    receipt_footer = models.TextField(
        blank=True,
        verbose_name='Pie de Ticket',
        help_text='Si está vacío, usa PRINTING_CONFIG["receipt_footer"] de settings.py'
    )
    
    # Configuración de impresión automática
    auto_print_receipt = models.BooleanField(
        default=True,
        verbose_name='Imprimir Ticket Automáticamente',
        help_text='Imprimir ticket al completar pago'
    )
    
    auto_print_kitchen = models.BooleanField(
        default=True,
        verbose_name='Imprimir Orden de Cocina Automáticamente',
        help_text='Imprimir orden de cocina al confirmar orden'
    )
    
    # Control de caja automático
    auto_open_drawer_on_payment = models.BooleanField(
        default=True,
        verbose_name='Abrir Caja Automáticamente al Pagar',
        help_text='Abrir caja al imprimir ticket de venta'
    )
    
    require_confirmation_to_open_drawer = models.BooleanField(
        default=False,
        verbose_name='Requiere Confirmación para Abrir Caja',
        help_text='Preguntar antes de abrir la caja'
    )
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Configuración de Impresión'
        verbose_name_plural = 'Configuraciones de Impresión'
    
    def __str__(self):
        return f'Configuración de {self.get_company_name()}'
    
    def save(self, *args, **kwargs):
        # Forzar singleton
        self.pk = 1
        super().save(*args, **kwargs)
        # Eliminar cualquier otro registro
        PrinterSettings.objects.exclude(pk=1).delete()
    
    # Métodos para obtener valores (BD o settings.py)
    
    def get_company_name(self):
        """Obtiene nombre de empresa (BD o settings)"""
        if self.company_name:
            return self.company_name
        
        from django.conf import settings
        return getattr(settings, 'COMPANY_CONFIG', {}).get('name', 'Mi Empresa')
    
    def get_company_address(self):
        """Obtiene dirección (BD o settings)"""
        if self.company_address:
            return self.company_address
        
        from django.conf import settings
        return getattr(settings, 'COMPANY_CONFIG', {}).get('address', 'Dirección no configurada')
    
    def get_company_phone(self):
        """Obtiene teléfono (BD o settings)"""
        if self.company_phone:
            return self.company_phone
        
        from django.conf import settings
        return getattr(settings, 'COMPANY_CONFIG', {}).get('phone', '000-0000')
    
    def get_company_email(self):
        """Obtiene email (BD o settings)"""
        if self.company_email:
            return self.company_email
        
        from django.conf import settings
        return getattr(settings, 'COMPANY_CONFIG', {}).get('email', '')
    
    def get_company_website(self):
        """Obtiene website (BD o settings)"""
        if self.company_website:
            return self.company_website
        
        from django.conf import settings
        return getattr(settings, 'COMPANY_CONFIG', {}).get('website', '')
    
    def get_tax_id(self):
        """Obtiene RUC/NIT (BD o settings)"""
        if self.tax_id:
            return self.tax_id
        
        from django.conf import settings
        return getattr(settings, 'COMPANY_CONFIG', {}).get('tax_id', '')
    
    def get_company_logo(self):
        """Obtiene logo (BD o settings)"""
        if self.company_logo:
            return self.company_logo
        
        from django.conf import settings
        logo_path = getattr(settings, 'COMPANY_CONFIG', {}).get('logo', '')
        
        if logo_path and not logo_path.startswith('data:'):
            # Es un path, convertir a path completo
            import os
            media_root = getattr(settings, 'MEDIA_ROOT', '')
            if media_root and not logo_path.startswith('/'):
                logo_path = os.path.join(media_root, logo_path)
        
        return logo_path
    
    def get_receipt_header(self):
        """Obtiene encabezado de ticket (BD o settings)"""
        if self.receipt_header:
            return self.receipt_header
        
        from django.conf import settings
        return getattr(settings, 'PRINTING_CONFIG', {}).get('receipt_header', '')
    
    def get_receipt_footer(self):
        """Obtiene pie de ticket (BD o settings)"""
        if self.receipt_footer:
            return self.receipt_footer
        
        from django.conf import settings
        return getattr(settings, 'PRINTING_CONFIG', {}).get('receipt_footer', '¡Gracias por su compra!')
    
    @classmethod
    def get_settings(cls):
        """Obtiene la configuración global (singleton)"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings