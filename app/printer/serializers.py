from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Printer, PrintJob, CashDrawerEvent, PrinterSettings

User = get_user_model()


# ============================================================================
# SERIALIZERS ESTÁNDAR (CRUD)
# ============================================================================

class PrinterSerializer(serializers.ModelSerializer):
    """Serializer para impresoras"""
    printer_type_display = serializers.CharField(source='get_printer_type_display', read_only=True)
    connection_type_display = serializers.CharField(source='get_connection_type_display', read_only=True)
    
    class Meta:
        model = Printer
        fields = [
            'id', 'name', 'printer_type', 'printer_type_display',
            'connection_type', 'connection_type_display',
            'connection_string', 'port', 'paper_width',
            'characters_per_line', 'has_cash_drawer',
            'cash_drawer_pin', 'cash_drawer_on_time',
            'cash_drawer_off_time', 'is_active', 'is_default',
            'config', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'connection_string': {'allow_blank': True, 'required': False}
        }


class PrintJobSerializer(serializers.ModelSerializer):
    """Serializer para trabajos de impresión"""
    printer_name = serializers.CharField(source='printer.name', read_only=True)
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = PrintJob
        fields = [
            'id', 'job_number', 'printer', 'printer_name',
            'document_type', 'document_type_display',
            'content', 'data', 'open_cash_drawer', 'cash_drawer_opened',
            'status', 'status_display', 'copies', 'error_message',
            'created_by', 'created_at', 'started_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'job_number', 'created_at', 
            'started_at', 'completed_at'
        ]


class CashDrawerEventSerializer(serializers.ModelSerializer):
    """Serializer para eventos de caja registradora"""
    printer_name = serializers.CharField(source='printer.name', read_only=True)
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    
    class Meta:
        model = CashDrawerEvent
        fields = [
            'id', 'printer', 'printer_name', 'print_job',
            'event_type', 'event_type_display', 'success',
            'notes', 'triggered_by', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PrinterSettingsSerializer(serializers.ModelSerializer):
    """Serializer para configuración global"""
    
    class Meta:
        model = PrinterSettings
        fields = [
            'id', 'company_logo', 'company_name', 'company_address',
            'company_phone', 'company_email', 'company_website',
            'tax_id', 'receipt_header', 'receipt_footer',
            'auto_print_receipt', 'auto_print_kitchen',
            'auto_open_drawer_on_payment',
            'require_confirmation_to_open_drawer',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# SERIALIZERS PARA PETICIONES DE IMPRESIÓN
# ============================================================================

class PrintRequestSerializer(serializers.Serializer):
    """Serializer para solicitudes de impresión directa"""
    printer = serializers.PrimaryKeyRelatedField(
        queryset=Printer.objects.filter(is_active=True)
    )
    content = serializers.CharField()
    document_type = serializers.ChoiceField(
        choices=PrintJob.DOCUMENT_TYPES,
        default='other'
    )
    open_cash_drawer = serializers.BooleanField(default=False)
    copies = serializers.IntegerField(default=1, min_value=1, max_value=10)


class TestConnectionSerializer(serializers.Serializer):
    """Serializer para prueba de conexión"""
    connection_type = serializers.ChoiceField(
        choices=Printer.CONNECTION_TYPES
    )
    connection_string = serializers.CharField(max_length=255)
    port = serializers.IntegerField(required=False, allow_null=True)


# ============================================================================
# SERIALIZERS PARA LA API DEL AGENTE DE WINDOWS
# ============================================================================

class AgenteImpresoraSerializer(serializers.Serializer):
    """Serializer para información de impresoras detectadas por el agente"""
    nombre = serializers.CharField(max_length=255)
    puerto = serializers.CharField(max_length=100, allow_blank=True, default='N/A')
    driver = serializers.CharField(max_length=255, allow_blank=True, default='N/A')
    estado = serializers.CharField(max_length=50, default='Disponible')


class AgenteRegistroSerializer(serializers.Serializer):
    """Serializer para registro del agente"""
    computadora = serializers.CharField(max_length=100)
    usuario = serializers.CharField(max_length=100)
    version_agente = serializers.CharField(max_length=20)
    impresoras = AgenteImpresoraSerializer(many=True)


class AgenteResultadoSerializer(serializers.Serializer):
    """Serializer para reporte de resultados del agente"""
    trabajo_id = serializers.UUIDField()
    success = serializers.BooleanField()
    mensaje = serializers.CharField(max_length=500, allow_blank=True, default='')
    detalles = serializers.JSONField(default=dict)


class AgenteEstadoSerializer(serializers.Serializer):
    """Serializer para estado del agente"""
    ejecutando = serializers.BooleanField()
    trabajos_exitosos = serializers.IntegerField()
    trabajos_fallidos = serializers.IntegerField()
    ultima_conexion = serializers.DateTimeField(allow_null=True)
    version_agente = serializers.CharField(max_length=20)
    computadora = serializers.CharField(max_length=100)
    usuario = serializers.CharField(max_length=100)