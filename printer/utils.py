import json
from datetime import datetime
from django.template import engines
from django.conf import settings
import qrcode
import base64
from io import BytesIO
from PIL import Image
import logging

logger = logging.getLogger(__name__)


class TemplateRenderer:
    """Renderizador de plantillas para impresión"""
    
    def __init__(self, template, data):
        self.template = template
        self.data = data
        self.settings = self.get_settings()
    
    def get_settings(self):
        """Obtiene configuración global"""
        from .models import PrinterSettings
        return PrinterSettings.get_settings()
    
    def render(self):
        """Renderiza la plantilla con los datos"""
        try:
            # Añadir datos comunes a todas las plantillas
            context = self.prepare_context()
            
            # Usar Django templates engine
            django_engine = engines['django']
            template_obj = django_engine.from_string(self.template.content)
            
            rendered = template_obj.render(context)
            
            # Procesar comandos especiales ESC/POS si es necesario
            if self.template.template_type in ['receipt', 'order_kitchen', 'order_bar']:
                rendered = self.add_escpos_commands(rendered)
            
            return rendered
            
        except Exception as e:
            logger.error(f"Error al renderizar plantilla: {str(e)}")
            raise
    
    def prepare_context(self):
        """Prepara el contexto con todos los datos necesarios"""
        context = {
            **self.data,
            'company': {
                'name': self.settings.company_name,
                'address': self.settings.company_address,
                'phone': self.settings.company_phone,
                'email': self.settings.company_email,
                'website': self.settings.company_website,
                'tax_id': self.settings.tax_id,
            },
            'header': self.settings.receipt_header,
            'footer': self.settings.receipt_footer,
            'now': datetime.now(),
            'settings': {
                'print_logo': self.template.print_logo,
                'print_qr': self.template.print_qr,
                'auto_cut': self.template.auto_cut,
            }
        }
        
        # Generar QR si está activado
        if self.template.print_qr:
            context['qr_code'] = self.generate_qr()
        
        return context
    
    def generate_qr(self):
        """Genera código QR con datos de la transacción"""
        qr_data = {
            'company': self.settings.company_name,
            'document_type': self.template.template_type,
            'timestamp': datetime.now().isoformat(),
        }
        
        # Añadir datos específicos según tipo de documento
        if 'order_number' in self.data:
            qr_data['order_number'] = self.data['order_number']
        if 'total' in self.data:
            qr_data['total'] = self.data['total']
        
        qr_text = json.dumps(qr_data)
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=3,
            border=2,
        )
        qr.add_data(qr_text)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convertir a base64 para plantillas HTML
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def add_escpos_commands(self, content):
        """Añade comandos ESC/POS al contenido para impresoras térmicas"""
        lines = content.split('\n')
        processed_lines = []
        
        for line in lines:
            processed_line = line
            
            # Comandos especiales entre corchetes
            if '[center]' in line:
                processed_line = line.replace('[center]', '')
                # En ESC/POS, el centrado se maneja diferente
                # Aquí solo quitamos el marcador
            
            if '[cut]' in line:
                processed_line = line.replace('[cut]', '')
                # El corte se manejará en el manager
            
            processed_lines.append(processed_line)
        
        return '\n'.join(processed_lines)