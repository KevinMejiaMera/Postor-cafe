from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import redirect
from django.contrib import messages
from .models import Printer, PrintJob, CashDrawerEvent, PrinterSettings


@admin.register(Printer)
class PrinterAdmin(admin.ModelAdmin):
    """Admin para impresoras - con prueba directa"""
    list_display = [
        'name', 'printer_type_badge', 'connection_type_badge',
        'connection_string', 'is_active_badge', 'is_default',
        'has_cash_drawer', 'action_buttons', 'created_at'
    ]
    list_filter = ['printer_type', 'connection_type', 'is_active', 'is_default', 'has_cash_drawer']
    search_fields = ['name', 'connection_string']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('id', 'name', 'printer_type', 'is_active', 'is_default')
        }),
        ('Conexión', {
            'fields': ('connection_type', 'connection_string', 'port')
        }),
        ('Configuración de Impresión', {
            'fields': ('paper_width', 'characters_per_line')
        }),
        ('Caja Registradora', {
            'fields': (
                'has_cash_drawer', 'cash_drawer_pin',
                'cash_drawer_on_time', 'cash_drawer_off_time'
            )
        }),
        ('Configuración Adicional', {
            'fields': ('config',),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def printer_type_badge(self, obj):
        colors = {
            'thermal': 'green',
            'laser': 'blue',
            'matrix': 'orange',
        }
        color = colors.get(obj.printer_type, 'gray')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_printer_type_display()
        )
    printer_type_badge.short_description = 'Tipo'
    
    def connection_type_badge(self, obj):
        icons = {
            'usb': '🔌',
            'network': '🌐',
            'bluetooth': '📡',
            'serial': '🔗',
        }
        icon = icons.get(obj.connection_type, '❓')
        return f'{icon} {obj.get_connection_type_display()}'
    connection_type_badge.short_description = 'Conexión'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color: green; font-weight: bold;">✅ Activa</span>'
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">❌ Inactiva</span>'
        )
    is_active_badge.short_description = 'Estado'
    
    def action_buttons(self, obj):
        """Botones de acción - DIRECTO sin confirmación"""
        from django.urls import reverse
        return format_html(
            '<a class="button" href="{}">🖨️ Prueba</a>&nbsp;'
            '<a class="button" href="{}">💰 Caja</a>',
            reverse('admin:printer_test_print_direct', args=[obj.pk]),
            reverse('admin:printer_test_drawer_direct', args=[obj.pk])
        )
    action_buttons.short_description = 'Acciones'
    
    def get_urls(self):
        """URLs para acciones directas"""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/test-print-direct/',
                self.admin_site.admin_view(self.test_print_direct),
                name='printer_test_print_direct',
            ),
            path(
                '<path:object_id>/test-drawer-direct/',
                self.admin_site.admin_view(self.test_drawer_direct),
                name='printer_test_drawer_direct',
            ),
        ]
        return custom_urls + urls
    
    def test_print_direct(self, request, object_id):
        """Imprime DIRECTO sin confirmación"""
        printer = self.get_object(request, object_id)
        
        try:
            from django.utils import timezone
            
            # Crear trabajo de prueba
            job = PrintJob.objects.create(
                printer=printer,
                document_type='other',
                content=f"""
╔════════════════════════════════════════╗
║     PRUEBA DE IMPRESION EXITOSA       ║
╚════════════════════════════════════════╝

Impresora: {printer.name}
Tipo: {printer.get_printer_type_display()}
Conexión: {printer.get_connection_type_display()}
Puerto/String: {printer.connection_string}
Ancho papel: {printer.paper_width}mm
Caracteres/línea: {printer.characters_per_line}

════════════════════════════════════════
           PRUEBAS DE FORMATO
════════════════════════════════════════

Texto normal
TEXTO EN MAYUSCULAS
texto en minusculas

════════════════════════════════════════
              INFORMACION
════════════════════════════════════════

Fecha: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}
Usuario: {request.user.username}

Caja registradora: {'✅ SI' if printer.has_cash_drawer else '❌ NO'}
Estado: {'✅ ACTIVA' if printer.is_active else '⚠️ INACTIVA'}
Por defecto: {'✅ SI' if printer.is_default else '❌ NO'}

════════════════════════════════════════

Si puede leer este mensaje, 
la impresora funciona correctamente.

════════════════════════════════════════
         *** FIN DE PRUEBA ***
════════════════════════════════════════
                """.strip(),
                status='pending',
                created_by=request.user.username,
                data={'test': True, 'admin_test': True}
            )
            
            messages.success(
                request,
                f'✅ Trabajo de prueba creado: {job.job_number}. '
                f'El agente lo imprimirá automáticamente en unos segundos.'
            )
            
            # Redirigir al detalle del trabajo
            return redirect('admin:printer_printjob_change', job.pk)
            
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')
            return redirect('admin:printer_printer_change', object_id)
    
    def test_drawer_direct(self, request, object_id):
        """Abre caja DIRECTO sin confirmación"""
        printer = self.get_object(request, object_id)
        
        if not printer.has_cash_drawer:
            messages.warning(request, '⚠️ Esta impresora no tiene caja registradora configurada')
            return redirect('admin:printer_printer_change', object_id)
        
        try:
            # Crear trabajo para abrir caja
            job = PrintJob.objects.create(
                printer=printer,
                document_type='other',
                content='Apertura manual de caja desde Admin',
                open_cash_drawer=True,
                status='pending',
                created_by=request.user.username,
                data={'test_drawer': True, 'admin_test': True}
            )
            
            # Registrar evento
            CashDrawerEvent.objects.create(
                printer=printer,
                print_job=job,
                event_type='test',
                success=True,
                notes='Prueba desde admin Django',
                triggered_by=request.user.username
            )
            
            messages.success(
                request,
                f'✅ Solicitud de apertura enviada: {job.job_number}. '
                f'El agente abrirá la caja en unos segundos.'
            )
            
            return redirect('admin:printer_printer_change', object_id)
            
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')
            return redirect('admin:printer_printer_change', object_id)
    
    # Acción masiva
    actions = ['test_selected_printers', 'open_drawer_selected']
    
    def test_selected_printers(self, request, queryset):
        """Probar múltiples impresoras"""
        count = 0
        jobs = []
        
        for printer in queryset:
            if printer.is_active:
                try:
                    job = PrintJob.objects.create(
                        printer=printer,
                        document_type='other',
                        content=f'Prueba masiva - {printer.name}',
                        status='pending',
                        created_by=request.user.username,
                        data={'mass_test': True}
                    )
                    jobs.append(job.job_number)
                    count += 1
                except Exception as e:
                    messages.warning(request, f'Error en {printer.name}: {str(e)}')
        
        if count > 0:
            messages.success(request, f'✅ {count} trabajo(s) creados: {", ".join(jobs)}')
        else:
            messages.warning(request, '⚠️ No se crearon trabajos')
    
    test_selected_printers.short_description = '🖨️ Probar impresoras seleccionadas'
    
    def open_drawer_selected(self, request, queryset):
        """Abrir caja de múltiples impresoras"""
        count = 0
        
        for printer in queryset:
            if printer.is_active and printer.has_cash_drawer:
                try:
                    job = PrintJob.objects.create(
                        printer=printer,
                        document_type='other',
                        content=f'Apertura masiva - {printer.name}',
                        open_cash_drawer=True,
                        status='pending',
                        created_by=request.user.username,
                        data={'mass_drawer': True}
                    )
                    count += 1
                except Exception as e:
                    messages.warning(request, f'Error en {printer.name}: {str(e)}')
        
        if count > 0:
            messages.success(request, f'✅ {count} solicitud(es) de apertura enviadas')
        else:
            messages.warning(request, '⚠️ No se enviaron solicitudes')
    
    open_drawer_selected.short_description = '💰 Abrir caja de seleccionadas'


@admin.register(PrintJob)
class PrintJobAdmin(admin.ModelAdmin):
    """Admin para trabajos de impresión"""
    list_display = [
        'job_number', 'document_type_badge', 'printer',
        'status_badge', 'copies', 'open_cash_drawer',
        'created_by', 'created_at'
    ]
    list_filter = ['status', 'document_type', 'printer', 'open_cash_drawer', 'created_at']
    search_fields = ['job_number', 'created_by', 'content']
    readonly_fields = [
        'id', 'job_number', 'created_at',
        'started_at', 'completed_at', 'cash_drawer_opened'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Información Básica', {
            'fields': (
                'id', 'job_number', 'status', 'document_type',
                'printer'
            )
        }),
        ('Contenido', {
            'fields': ('content', 'data')
        }),
        ('Configuración', {
            'fields': ('copies', 'open_cash_drawer', 'cash_drawer_opened')
        }),
        ('Resultado', {
            'fields': ('error_message',)
        }),
        ('Auditoría', {
            'fields': (
                'created_by', 'created_at',
                'started_at', 'completed_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def document_type_badge(self, obj):
        icons = {
            'receipt': '🧾',
            'invoice': '📄',
            'order': '📋',
            'report': '📊',
            'other': '📝',
        }
        icon = icons.get(obj.document_type, '📝')
        return f'{icon} {obj.get_document_type_display()}'
    document_type_badge.short_description = 'Tipo'
    
    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'printing': 'blue',
            'completed': 'green',
            'failed': 'red',
            'cancelled': 'gray',
        }
        icons = {
            'pending': '⏳',
            'printing': '🖨️',
            'completed': '✅',
            'failed': '❌',
            'cancelled': '🚫',
        }
        color = colors.get(obj.status, 'gray')
        icon = icons.get(obj.status, '❓')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{} {}</span>',
            color,
            icon,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'
    
    actions = ['mark_as_cancelled', 'retry_failed_jobs']
    
    def mark_as_cancelled(self, request, queryset):
        """Cancelar trabajos"""
        count = 0
        for job in queryset:
            if job.status in ['pending', 'printing']:
                job.status = 'cancelled'
                job.save(update_fields=['status'])
                count += 1
        
        self.message_user(request, f'✅ {count} trabajo(s) cancelado(s)')
    
    mark_as_cancelled.short_description = '🚫 Cancelar seleccionados'
    
    def retry_failed_jobs(self, request, queryset):
        """Reintentar fallidos"""
        count = 0
        for job in queryset.filter(status='failed'):
            job.status = 'pending'
            job.error_message = ''
            job.save(update_fields=['status', 'error_message'])
            count += 1
        
        self.message_user(request, f'✅ {count} trabajo(s) marcado(s) para reintento')
    
    retry_failed_jobs.short_description = '🔄 Reintentar fallidos'


@admin.register(CashDrawerEvent)
class CashDrawerEventAdmin(admin.ModelAdmin):
    """Admin para eventos de caja"""
    list_display = [
        'printer', 'event_type_badge', 'success_badge',
        'print_job_link', 'triggered_by', 'created_at'
    ]
    list_filter = ['event_type', 'success', 'printer', 'created_at']
    search_fields = ['notes', 'triggered_by']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('id', 'printer', 'print_job', 'event_type', 'success')
        }),
        ('Detalles', {
            'fields': ('notes', 'triggered_by', 'created_at')
        }),
    )
    
    def event_type_badge(self, obj):
        icons = {
            'print': '🖨️',
            'manual': '🔓',
            'register_open': '🟢',
            'register_close': '🔴',
            'test': '🧪',
        }
        icon = icons.get(obj.event_type, '❓')
        return f'{icon} {obj.get_event_type_display()}'
    event_type_badge.short_description = 'Tipo'
    
    def success_badge(self, obj):
        if obj.success:
            return format_html('<span style="color: green; font-weight: bold;">✅ Exitoso</span>')
        return format_html('<span style="color: red; font-weight: bold;">❌ Fallido</span>')
    success_badge.short_description = 'Resultado'
    
    def print_job_link(self, obj):
        if obj.print_job:
            from django.urls import reverse
            url = reverse('admin:printer_printjob_change', args=[obj.print_job.pk])
            return format_html('<a href="{}">{}</a>', url, obj.print_job.job_number)
        return '-'
    print_job_link.short_description = 'Trabajo'


@admin.register(PrinterSettings)
class PrinterSettingsAdmin(admin.ModelAdmin):
    """Admin para configuración global"""
    
    fieldsets = (
        ('Información de la Empresa', {
            'fields': (
                'company_name', 'company_address',
                'company_phone', 'company_email',
                'company_website', 'tax_id'
            )
        }),
        ('Logo', {
            'fields': ('company_logo',),
            'description': 'Imagen en base64 o ruta al archivo'
        }),
        ('Mensajes Personalizados', {
            'fields': ('receipt_header', 'receipt_footer')
        }),
        ('Configuración de Impresión Automática', {
            'fields': (
                'auto_print_receipt',
                'auto_print_kitchen'
            )
        }),
        ('Control de Caja Registradora', {
            'fields': (
                'auto_open_drawer_on_payment',
                'require_confirmation_to_open_drawer'
            )
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def has_add_permission(self, request):
        return not PrinterSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False