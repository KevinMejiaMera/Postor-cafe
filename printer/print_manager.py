"""
Print Manager - Gestor de Impresión con Comandos ESC/POS
Maneja toda la lógica de generación de comandos para impresoras térmicas
"""

import logging
from io import BytesIO
from PIL import Image
import base64
import os

logger = logging.getLogger(__name__)


class ESCPOSCommands:
    """Comandos ESC/POS estándar para impresoras térmicas"""
    
    # Caracteres de control
    ESC = b'\x1b'
    GS = b'\x1d'
    LF = b'\n'
    
    # Inicialización
    INITIALIZE = ESC + b'@'
    
    # Alineación
    ALIGN_LEFT = ESC + b'a' + b'\x00'
    ALIGN_CENTER = ESC + b'a' + b'\x01'
    ALIGN_RIGHT = ESC + b'a' + b'\x02'
    
    # Texto
    TEXT_NORMAL = ESC + b'!' + b'\x00'
    TEXT_BOLD_ON = ESC + b'E' + b'\x01'
    TEXT_BOLD_OFF = ESC + b'E' + b'\x00'
    TEXT_UNDERLINE_ON = ESC + b'-' + b'\x01'
    TEXT_UNDERLINE_OFF = ESC + b'-' + b'\x00'
    TEXT_DOUBLE_HEIGHT = ESC + b'!' + b'\x10'
    TEXT_DOUBLE_WIDTH = ESC + b'!' + b'\x20'
    TEXT_DOUBLE_SIZE = ESC + b'!' + b'\x30'
    
    # Tamaños de fuente (usando GS !)
    @staticmethod
    def font_size(width=1, height=1):
        """
        Establece tamaño de fuente
        width: 1-8 (multiplicador de ancho)
        height: 1-8 (multiplicador de alto)
        """
        size = ((width - 1) << 4) | (height - 1)
        return ESCPOSCommands.GS + b'!' + bytes([size])
    
    # Corte de papel
    CUT_FULL = GS + b'V' + b'\x00'  # Corte completo
    CUT_PARTIAL = GS + b'\x56' + b'\x01'  # Corte parcial
    CUT_FEED_AND_CUT = GS + b'V' + b'\x41' + b'\x00'  # Alimentar y cortar
    
    @staticmethod
    def cut_paper(feed_lines=4):
        """
        Corta el papel después de alimentar líneas
        feed_lines: número de líneas a alimentar antes de cortar (0-255)
        """
        return ESCPOSCommands.GS + b'V' + b'\x42' + bytes([feed_lines])
    
    # Caja registradora
    @staticmethod
    def open_cash_drawer(pin=0, on_time=100, off_time=100):
        """
        Abre la caja registradora
        pin: 0 (pin 2) o 1 (pin 5)
        on_time: tiempo ON en ms (0-255) - multiplicar por 2ms
        off_time: tiempo OFF en ms (0-255) - multiplicar por 2ms
        """
        # Convertir milisegundos a unidades de 2ms
        on_units = min(255, max(1, on_time // 2))
        off_units = min(255, max(1, off_time // 2))
        
        return ESCPOSCommands.ESC + b'p' + bytes([pin, on_units, off_units])
    
    # Código de barras
    @staticmethod
    def barcode(data, barcode_type=73):
        """
        Imprime código de barras
        barcode_type: 73 = CODE128
        """
        commands = bytearray()
        commands.extend(ESCPOSCommands.GS + b'h' + b'\x64')  # Altura
        commands.extend(ESCPOSCommands.GS + b'w' + b'\x03')  # Ancho
        commands.extend(ESCPOSCommands.GS + b'k' + bytes([barcode_type]))
        commands.extend(data.encode('ascii'))
        commands.extend(b'\x00')  # NULL terminator
        return bytes(commands)
    
    # QR Code
    @staticmethod
    def qr_code(data, size=6):
        """
        Imprime código QR
        size: 1-16 (tamaño del módulo)
        """
        commands = bytearray()
        
        # Modelo QR (Modelo 2)
        commands.extend(ESCPOSCommands.GS + b'(' + b'k' + b'\x04\x00' + b'\x31\x41' + b'\x32\x00')
        
        # Tamaño del módulo
        commands.extend(ESCPOSCommands.GS + b'(' + b'k' + b'\x03\x00' + b'\x31\x43' + bytes([size]))
        
        # Nivel de corrección de error (L=48, M=49, Q=50, H=51)
        commands.extend(ESCPOSCommands.GS + b'(' + b'k' + b'\x03\x00' + b'\x31\x45' + b'\x31')
        
        # Almacenar datos
        data_bytes = data.encode('utf-8')
        data_len = len(data_bytes) + 3
        pl = data_len & 0xFF
        ph = (data_len >> 8) & 0xFF
        commands.extend(ESCPOSCommands.GS + b'(' + b'k' + bytes([pl, ph]) + b'\x31\x50\x30')
        commands.extend(data_bytes)
        
        # Imprimir QR
        commands.extend(ESCPOSCommands.GS + b'(' + b'k' + b'\x03\x00' + b'\x31\x51\x30')
        
        return bytes(commands)
    
    # Imagen
    @staticmethod
    def image_raster(image_data):
        """
        Imprime imagen en modo raster
        image_data: bytes de la imagen procesada
        """
        # Implementación básica - necesita procesamiento de imagen
        return ESCPOSCommands.GS + b'v' + b'0' + b'\x00' + image_data


class PrinterManager:
    """Gestor principal de impresión"""
    
    @staticmethod
    def generate_print_commands(print_job):
        """
        Genera comandos ESC/POS completos para un trabajo de impresión
        
        Args:
            print_job: Objeto PrintJob
            
        Returns:
            str: Comandos en hexadecimal
        """
        from .models import PrinterSettings
        
        printer = print_job.printer
        settings = PrinterSettings.get_settings()
        
        commands = bytearray()
        
        # 1. INICIALIZAR IMPRESORA
        commands.extend(ESCPOSCommands.INITIALIZE)
        
        # 2. LOGO (si existe en los datos del trabajo)
        logo_path = print_job.data.get('logo_path')
        if logo_path and os.path.exists(logo_path):
            try:
                logo_commands = PrinterManager._process_logo(logo_path, printer)
                if logo_commands:
                    commands.extend(logo_commands)
                    commands.extend(ESCPOSCommands.LF * 2)  # Espacio después del logo
            except Exception as e:
                logger.warning(f"No se pudo imprimir logo: {e}")
        
        # 3. CONTENIDO
        # Procesar el contenido línea por línea para aplicar formatos
        lines = print_job.content.split('\n')
        
        for line in lines:
            # Detectar y aplicar formatos especiales
            if line.strip().startswith('=') and line.strip().endswith('='):
                # Línea de separación gruesa
                commands.extend(ESCPOSCommands.TEXT_BOLD_ON)
                commands.extend(line.encode('utf-8', errors='ignore'))
                commands.extend(ESCPOSCommands.TEXT_BOLD_OFF)
                commands.extend(ESCPOSCommands.LF)
                
            elif line.strip().startswith('-') and line.strip().endswith('-'):
                # Línea de separación delgada
                commands.extend(line.encode('utf-8', errors='ignore'))
                commands.extend(ESCPOSCommands.LF)
                
            elif 'TOTAL' in line.upper():
                # Líneas de total en negrita y tamaño grande
                commands.extend(ESCPOSCommands.font_size(2, 2))
                commands.extend(ESCPOSCommands.TEXT_BOLD_ON)
                commands.extend(line.encode('utf-8', errors='ignore'))
                commands.extend(ESCPOSCommands.TEXT_BOLD_OFF)
                commands.extend(ESCPOSCommands.TEXT_NORMAL)
                commands.extend(ESCPOSCommands.LF)
                
            elif line.strip().upper() in ['TICKET DE VENTA', 'FACTURA', 'COMPROBANTE']:
                # Títulos centrados y en grande
                commands.extend(ESCPOSCommands.ALIGN_CENTER)
                commands.extend(ESCPOSCommands.font_size(2, 2))
                commands.extend(ESCPOSCommands.TEXT_BOLD_ON)
                commands.extend(line.encode('utf-8', errors='ignore'))
                commands.extend(ESCPOSCommands.TEXT_BOLD_OFF)
                commands.extend(ESCPOSCommands.TEXT_NORMAL)
                commands.extend(ESCPOSCommands.ALIGN_LEFT)
                commands.extend(ESCPOSCommands.LF)
                
            else:
                # Línea normal
                commands.extend(line.encode('utf-8', errors='ignore'))
                commands.extend(ESCPOSCommands.LF)
        
        # 4. CÓDIGO QR (si está en los datos)
        qr_data = print_job.data.get('qr_code')
        if qr_data:
            try:
                commands.extend(ESCPOSCommands.ALIGN_CENTER)
                commands.extend(ESCPOSCommands.LF * 2)
                commands.extend(ESCPOSCommands.qr_code(qr_data, size=6))
                commands.extend(ESCPOSCommands.LF * 2)
                commands.extend(ESCPOSCommands.ALIGN_LEFT)
            except Exception as e:
                logger.warning(f"No se pudo imprimir QR: {e}")
        
        # 5. CÓDIGO DE BARRAS (si está en los datos)
        barcode_data = print_job.data.get('barcode')
        if barcode_data:
            try:
                commands.extend(ESCPOSCommands.ALIGN_CENTER)
                commands.extend(ESCPOSCommands.LF)
                commands.extend(ESCPOSCommands.barcode(barcode_data))
                commands.extend(ESCPOSCommands.LF * 2)
                commands.extend(ESCPOSCommands.ALIGN_LEFT)
            except Exception as e:
                logger.warning(f"No se pudo imprimir código de barras: {e}")
        
        # 6. ALIMENTAR PAPEL ANTES DE CORTAR
        commands.extend(ESCPOSCommands.LF * 4)
        
        # 7. CORTAR PAPEL
        commands.extend(ESCPOSCommands.CUT_FEED_AND_CUT)
        
        # 8. ABRIR CAJA REGISTRADORA (si está configurado)
        if print_job.open_cash_drawer and printer.has_cash_drawer:
            commands.extend(ESCPOSCommands.open_cash_drawer(
                pin=printer.cash_drawer_pin,
                on_time=printer.cash_drawer_on_time,
                off_time=printer.cash_drawer_off_time
            ))
        
        # Convertir a hexadecimal
        return commands.hex()
    
    @staticmethod
    def _process_logo(logo_path, printer):
        """
        Procesa y convierte logo a comandos ESC/POS
        
        Args:
            logo_path: Ruta del archivo de imagen
            printer: Objeto Printer
            
        Returns:
            bytes: Comandos ESC/POS para imprimir el logo
        """
        try:
            # Abrir imagen
            image = Image.open(logo_path)
            
            # Convertir a escala de grises
            image = image.convert('L')
            
            # Redimensionar según ancho de papel
            if printer.paper_width >= 80:
                max_width = 512
            elif printer.paper_width >= 58:
                max_width = 360
            else:
                max_width = 256
            
            if image.width > max_width:
                aspect_ratio = image.height / image.width
                new_width = max_width
                new_height = int(new_width * aspect_ratio)
                image = image.resize((new_width, new_height), Image.LANCZOS)
            
            # Convertir a 1-bit (blanco y negro)
            image = image.point(lambda x: 0 if x < 128 else 255, '1')
            
            # Convertir a formato de bits para impresora
            width = image.width
            height = image.height
            
            # La imagen debe ser múltiplo de 8 en ancho
            if width % 8 != 0:
                new_width = ((width // 8) + 1) * 8
                new_image = Image.new('1', (new_width, height), 1)
                new_image.paste(image, (0, 0))
                image = new_image
                width = new_width
            
            # Convertir pixels a bytes
            image_data = bytearray()
            pixels = list(image.getdata())
            
            for y in range(height):
                row_data = []
                for x in range(0, width, 8):
                    byte = 0
                    for bit in range(8):
                        if x + bit < width:
                            pixel_index = y * width + x + bit
                            if pixel_index < len(pixels):
                                if pixels[pixel_index] == 0:  # Negro
                                    byte |= (1 << (7 - bit))
                        row_data.append(byte)
                image_data.extend(row_data)
            
            # Generar comandos ESC/POS para imagen
            commands = bytearray()
            
            # Centrar imagen
            commands.extend(ESCPOSCommands.ALIGN_CENTER)
            
            # Comando GS v 0 (imprimir imagen raster)
            width_bytes = width // 8
            xl = width_bytes & 0xFF
            xh = (width_bytes >> 8) & 0xFF
            yl = height & 0xFF
            yh = (height >> 8) & 0xFF
            
            commands.extend(ESCPOSCommands.GS + b'v' + b'0' + b'\x00')
            commands.extend(bytes([xl, xh, yl, yh]))
            commands.extend(image_data)
            
            # Volver a alineación izquierda
            commands.extend(ESCPOSCommands.ALIGN_LEFT)
            
            return bytes(commands)
            
        except Exception as e:
            logger.error(f"Error procesando logo: {str(e)}")
            return None
    
    @staticmethod
    def generate_open_drawer_commands(printer):
        """
        Genera comandos solo para abrir caja registradora
        
        Args:
            printer: Objeto Printer
            
        Returns:
            str: Comandos en hexadecimal
        """
        commands = bytearray()
        
        commands.extend(ESCPOSCommands.open_cash_drawer(
            pin=printer.cash_drawer_pin,
            on_time=printer.cash_drawer_on_time,
            off_time=printer.cash_drawer_off_time
        ))
        
        return commands.hex()
    
    @staticmethod
    def generate_test_page_commands(printer):
        """
        Genera comandos para página de prueba
        
        Args:
            printer: Objeto Printer
            
        Returns:
            str: Comandos en hexadecimal
        """
        from django.utils import timezone
        
        commands = bytearray()
        
        # Inicializar
        commands.extend(ESCPOSCommands.INITIALIZE)
        
        # Título centrado
        commands.extend(ESCPOSCommands.ALIGN_CENTER)
        commands.extend(ESCPOSCommands.font_size(2, 2))
        commands.extend(ESCPOSCommands.TEXT_BOLD_ON)
        commands.extend(b'PRUEBA DE IMPRESION')
        commands.extend(ESCPOSCommands.TEXT_BOLD_OFF)
        commands.extend(ESCPOSCommands.TEXT_NORMAL)
        commands.extend(ESCPOSCommands.LF * 2)
        
        # Información de la impresora
        commands.extend(ESCPOSCommands.ALIGN_LEFT)
        commands.extend(f'Impresora: {printer.name}\n'.encode('utf-8'))
        commands.extend(f'Tipo: {printer.get_printer_type_display()}\n'.encode('utf-8'))
        commands.extend(f'Conexion: {printer.get_connection_type_display()}\n'.encode('utf-8'))
        commands.extend(f'Ancho papel: {printer.paper_width}mm\n'.encode('utf-8'))
        commands.extend(f'Caja: {"Si" if printer.has_cash_drawer else "No"}\n'.encode('utf-8'))
        commands.extend(ESCPOSCommands.LF)
        
        commands.extend(f'Fecha: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}\n'.encode('utf-8'))
        commands.extend(ESCPOSCommands.LF)
        
        # Línea de separación
        commands.extend(b'=' * 42)
        commands.extend(ESCPOSCommands.LF * 2)
        
        # Prueba de formatos
        commands.extend(b'Texto normal\n')
        commands.extend(ESCPOSCommands.TEXT_BOLD_ON)
        commands.extend(b'Texto en negrita\n')
        commands.extend(ESCPOSCommands.TEXT_BOLD_OFF)
        commands.extend(ESCPOSCommands.TEXT_UNDERLINE_ON)
        commands.extend(b'Texto subrayado\n')
        commands.extend(ESCPOSCommands.TEXT_UNDERLINE_OFF)
        commands.extend(ESCPOSCommands.LF)
        
        # Prueba de tamaños
        commands.extend(ESCPOSCommands.font_size(1, 1))
        commands.extend(b'Tamano normal\n')
        commands.extend(ESCPOSCommands.font_size(2, 2))
        commands.extend(b'Tamano 2x\n')
        commands.extend(ESCPOSCommands.TEXT_NORMAL)
        commands.extend(ESCPOSCommands.LF)
        
        # Prueba de alineación
        commands.extend(ESCPOSCommands.ALIGN_LEFT)
        commands.extend(b'Izquierda\n')
        commands.extend(ESCPOSCommands.ALIGN_CENTER)
        commands.extend(b'Centro\n')
        commands.extend(ESCPOSCommands.ALIGN_RIGHT)
        commands.extend(b'Derecha\n')
        commands.extend(ESCPOSCommands.ALIGN_LEFT)
        commands.extend(ESCPOSCommands.LF)
        
        # Código QR de prueba
        commands.extend(ESCPOSCommands.ALIGN_CENTER)
        commands.extend(b'Codigo QR de prueba:\n')
        commands.extend(ESCPOSCommands.qr_code('https://agrototal.ec', size=4))
        commands.extend(ESCPOSCommands.LF * 2)
        
        # Fin
        commands.extend(ESCPOSCommands.ALIGN_CENTER)
        commands.extend(b'*** FIN DE PRUEBA ***\n')
        commands.extend(ESCPOSCommands.LF * 4)
        
        # Cortar papel
        commands.extend(ESCPOSCommands.CUT_FEED_AND_CUT)
        
        return commands.hex()
    
    @staticmethod
    def print_test_page(printer, user='system'):
        """
        MÉTODO AUXILIAR - Para compatibilidad con código existente
        (Este método no imprime directamente, solo genera el trabajo)
        """
        from .models import PrintJob
        
        try:
            # Crear trabajo de prueba
            test_content = f"""
            PRUEBA DE IMPRESION
            
            Impresora: {printer.name}
            Tipo: {printer.get_printer_type_display()}
            Usuario: {user}
            
            Esta es una prueba de impresion.
            Si puede leer esto, la impresora funciona correctamente.
            
            *** FIN DE PRUEBA ***
            """
            
            job = PrintJob.objects.create(
                printer=printer,
                document_type='other',
                content=test_content.strip(),
                status='pending',
                created_by=user
            )
            
            return True, f"Trabajo de prueba creado: {job.job_number}"
            
        except Exception as e:
            return False, f"Error creando trabajo de prueba: {str(e)}"
    
    @staticmethod
    def open_cash_drawer(printer):
        """
        MÉTODO AUXILIAR - Para compatibilidad con código existente
        """
        from .models import PrintJob
        
        try:
            job = PrintJob.objects.create(
                printer=printer,
                document_type='other',
                content='Apertura manual de caja',
                open_cash_drawer=True,
                status='pending',
                created_by='system'
            )
            
            return True, "Solicitud de apertura enviada"
            
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    @staticmethod
    def check_connection(printer):
        """
        MÉTODO AUXILIAR - Verifica conexión (siempre retorna 'online' para el agente)
        """
        # El agente es quien realmente verifica la conexión
        return 'online' if printer.is_active else 'offline'
    
    @staticmethod
    def test_connection(connection_type, connection_string, port=None):
        """
        MÉTODO AUXILIAR - Prueba de conexión básica
        """
        # Validación básica
        if not connection_string:
            return False, "Cadena de conexión vacía"
        
        if connection_type == 'network' and not port:
            return False, "Puerto requerido para conexión de red"
        
        return True, "Configuración válida (prueba real se hace en el agente)"
    
    @staticmethod
    def print_job(print_job):
        """
        MÉTODO AUXILIAR - Para compatibilidad
        El agente es quien realmente imprime
        """
        # En este modelo, los trabajos se marcan como pending
        # y el agente los procesa
        return True, "Trabajo marcado como pendiente para el agente"