
# 📁 usuarios/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import CrearUsuarioForm, EditarUsuarioForm
from django.db.models import Q, Sum, F
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone 
from .models import Usuario, AuditLog
from pedidos.models import Pedido, Mesa, Producto, Factura, DetallePedido
from inventario.models import Insumo
from caja.models import SesionCaja, Gasto
from django.utils.dateparse import parse_date
import datetime
import csv
import json
from django.db.models.functions import TruncDay
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

# Helper functions
def es_gerente(user):
    return user.is_authenticated and (user.rol == 'gerente' or user.rol == 'admin' or user.is_superuser)

# 1. LOGIN
def login_view(request):
    if request.user.is_authenticated:
        if request.user.rol == 'mesero':
            return redirect('usuarios:dashboard_mesero')
        elif request.user.rol == 'cocina':
            return redirect('pedidos:dashboard_cocina')
        elif request.user.rol == 'gerente':
            return redirect('usuarios:dashboard_gerente')
        elif request.user.rol == 'admin':
            return redirect('admin:index')

    if request.method == 'POST':
        identifier = request.POST.get('identifier')
        password = request.POST.get('password')

        if not identifier or not password:
            messages.error(request, 'Por favor, ingrese su usuario/correo y contraseña.')
            return render(request, 'usuarios/login.html')

        try:
            user_q = Usuario.objects.get(Q(username=identifier) | Q(email=identifier))
            user = authenticate(request, username=user_q.username, password=password)

            if user is not None:
                login(request, user)
                # Agregamos ?init_session=true para que el frontend active la "sessionStorage"
                if user.rol == 'mesero':
                    return redirect(reverse('usuarios:dashboard_mesero') + '?init_session=true')
                elif user.rol == 'cocina':
                    return redirect(reverse('pedidos:dashboard_cocina') + '?init_session=true')
                elif user.rol == 'gerente':
                    return redirect(reverse('usuarios:dashboard_gerente') + '?init_session=true')
                elif user.rol == 'admin':
                    return redirect('/admin/')
                else:
                    return redirect('/') 
            else:
                messages.error(request, 'Credenciales inválidas.')
        
        except Usuario.DoesNotExist:
            messages.error(request, 'Credenciales inválidas.')

    return render(request, 'usuarios/login.html')

# 2. LOGOUT
def logout_view(request):
    logout(request)
    messages.success(request, 'Has cerrado sesión exitosamente.')
    return redirect('usuarios:login')

# 3. DASHBOARD MESERO
@login_required
def dashboard_mesero(request):
    if request.user.rol != 'mesero':
        return redirect('usuarios:login')
    mesas = Mesa.objects.all().order_by('numero')
    return render(request, 'usuarios/dashboard_mesero.html', {'mesas': mesas})

# 4. DASHBOARD GERENTE (LA QUE FALTABA)
@login_required
def dashboard_gerente(request):
    if request.user.rol != 'gerente' and request.user.rol != 'admin':
        return redirect('usuarios:login')

    # Datos para las Tarjetas
    total_usuarios = Usuario.objects.count()
    
    # Usuarios ONLINE (Actividad en últimos 5 minutos)
    hace_5_minutos = timezone.now() - timezone.timedelta(minutes=5)
    usuarios_online = Usuario.objects.filter(last_activity__gte=hace_5_minutos).count()
    usuarios_activos = usuarios_online # Reemplazamos la variable para el template
    
    # Ventas de HOY
    hoy = timezone.localdate()
    # Modificado: Usamos Factura.fecha_emision para sumar lo que realmente se facturó/cobró hoy
    facturas_hoy = Factura.objects.filter(fecha_emision__date=hoy)
    total_ventas_hoy = facturas_hoy.aggregate(Sum('total'))['total__sum'] or 0
    
    # Logs
    ultimos_logs = AuditLog.objects.select_related('user').order_by('-timestamp')[:10]

    # --- DATOS PARA GRÁFICOS ---
    
    # 1. Ventas de la Semana (Últimos 7 días)
    fechas_grafico = []
    ventas_grafico = []
    # hoy ya está definido arriba como timezone.localdate()
    # hoy = timezone.now().date() <-- ELIMINADO
    
    for i in range(6, -1, -1):
        fecha = hoy - timezone.timedelta(days=i)
        # Filtramos facturas de ese día
        venta_dia = Factura.objects.filter(fecha_emision__date=fecha).aggregate(Sum('total'))['total__sum'] or 0
        
        # Formato fecha: "Lun 12"
        fechas_grafico.append(fecha.strftime("%d/%m")) 
        ventas_grafico.append(float(venta_dia))

    top_productos_q = DetallePedido.objects.filter(pedido__estado='pagado') \
        .values('producto__nombre') \
        .annotate(total_vendido=Sum('cantidad')) \
        .order_by('-total_vendido')[:5]

    top_labels = [item['producto__nombre'] for item in top_productos_q]
    top_data = [item['total_vendido'] for item in top_productos_q]

    context = {
        'total_usuarios': total_usuarios,
        'usuarios_activos': usuarios_activos,
        'total_ventas_hoy': total_ventas_hoy,
        'ultimos_logs': ultimos_logs,
        'pedidos_completados_hoy': facturas_hoy.count(), # Corregido: Usamos facturas_hoy
        
        # Datos JSON para JS
        'fechas_grafico': fechas_grafico,
        'ventas_grafico': ventas_grafico,
        'top_labels': top_labels,
        'top_data': top_data,
        
        # Nueva métrica: Ventas Semana Actual
        'ventas_semana_actual': sum(ventas_grafico), # Suma ventas de los últimos 7 días (aprox semana)
    }
    return render(request, 'usuarios/dashboard_gerente.html', context)

@login_required
def lista_usuarios(request):
    # Seguridad: Solo gerentes o admins
    if request.user.rol != 'gerente' and request.user.rol != 'admin':
        return redirect('usuarios:login')
        
    usuarios = Usuario.objects.all().order_by('-last_activity')
    time_threshold = timezone.now() - timezone.timedelta(minutes=5)

    return render(request, 'usuarios/lista_usuarios.html', {
        'usuarios': usuarios,
        'time_threshold': time_threshold
    })

@login_required
def gestion_menu(request):
    # Seguridad: Solo gerentes o admins
    if request.user.rol != 'gerente' and request.user.rol != 'admin':
        return redirect('usuarios:login')

    # Traemos todos los productos
    productos = Producto.objects.all().order_by('nombre')
    
    return render(request, 'usuarios/gestion_menu.html', {'productos': productos})

@login_required
def reportes_ventas(request):
    # Seguridad: Solo Gerentes o Admins
    if not es_gerente(request.user):
        return redirect('usuarios:login')

    # Filtros de Fecha Rápidos
    filtro_rapido = request.GET.get('filtro', '') # 'hoy', 'ayer', 'semana', 'caja_x'
    
    # Filtros de Fecha Personalizados
    fecha_inicio_str = request.GET.get('fecha_inicio')
    fecha_fin_str = request.GET.get('fecha_fin')
    
    # Rango de fechas por defecto a analizar
    fecha_inicio = None
    fecha_fin = None
    sesion_filtrada = None
    
    hoy = timezone.localdate()
    ayer = hoy - datetime.timedelta(days=1)
    
    if filtro_rapido == 'hoy':
        fecha_inicio = hoy
        fecha_fin = hoy
        fecha_inicio_str = hoy.strftime('%Y-%m-%d')
        fecha_fin_str = fecha_inicio_str
    elif filtro_rapido == 'ayer':
        fecha_inicio = ayer
        fecha_fin = ayer
        fecha_inicio_str = ayer.strftime('%Y-%m-%d')
        fecha_fin_str = fecha_inicio_str
    elif filtro_rapido == 'semana':
        semana_pasada = hoy - datetime.timedelta(days=7)
        fecha_inicio = semana_pasada
        fecha_fin = hoy
        fecha_inicio_str = semana_pasada.strftime('%Y-%m-%d')
        fecha_fin_str = hoy.strftime('%Y-%m-%d')
    elif filtro_rapido.startswith('caja_'):
        try:
            caja_id = int(filtro_rapido.split('_')[1])
            sesion_filtrada = SesionCaja.objects.get(id=caja_id)
        except:
            pass
    else:
        # Fechas enviadas por formulario
        if fecha_inicio_str and fecha_fin_str:
            fecha_inicio = parse_date(fecha_inicio_str)
            fecha_fin = parse_date(fecha_fin_str)
            
    # Query Base: Detalles de Pedidos Pagados
    detalles = DetallePedido.objects.filter(pedido__estado='pagado')

    # Aplicar Filtros de fechas en base a la factura asociada
    if sesion_filtrada:
        # Si filtramos por turno (caja), usamos sus datetimes exactos
        if sesion_filtrada.fecha_cierre:
            detalles = detalles.filter(
                pedido__factura__fecha_emision__gte=sesion_filtrada.fecha_apertura,
                pedido__factura__fecha_emision__lte=sesion_filtrada.fecha_cierre
            )
        else:
            # Caja aún abierta
            detalles = detalles.filter(
                pedido__factura__fecha_emision__gte=sesion_filtrada.fecha_apertura
            )
    elif fecha_inicio and fecha_fin:
        detalles = detalles.filter(pedido__factura__fecha_emision__date__range=[fecha_inicio, fecha_fin])
        
    # Obtener el reporte resumido de Productos Vendidos
    from django.db.models import F
    reporte_productos = detalles.values('producto__nombre', 'precio_unitario').annotate(
        cantidad_vendida=Sum('cantidad'),
        total=Sum(F('cantidad') * F('precio_unitario'))
    ).order_by('-cantidad_vendida')
    
    total_ingresos = sum([item['total'] for item in reporte_productos])
    
    # --- PROCESAR GASTOS (NUEVO) ---
    gastos_query = Gasto.objects.filter(modulo='restaurante')
    if sesion_filtrada:
        if sesion_filtrada.fecha_cierre:
            gastos_query = gastos_query.filter(fecha__gte=sesion_filtrada.fecha_apertura, fecha__lte=sesion_filtrada.fecha_cierre)
        else:
            gastos_query = gastos_query.filter(fecha__gte=sesion_filtrada.fecha_apertura)
    elif fecha_inicio and fecha_fin:
        gastos_query = gastos_query.filter(fecha__date__range=[fecha_inicio, fecha_fin])
    
    total_gastos = gastos_query.aggregate(Sum('monto'))['monto__sum'] or 0
    ganancia_neta = total_ingresos - total_gastos
    
    # Obtener las Cajas Recientes para el Sidebar (Solo de hoy y ayer)
    cajas_recientes = SesionCaja.objects.filter(fecha_apertura__date__gte=ayer).order_by('-fecha_apertura')

    return render(request, 'usuarios/reportes.html', {
        'total_ingresos': total_ingresos,
        'total_gastos': total_gastos,
        'ganancia_neta': ganancia_neta,
        'detalles_gastos': gastos_query.order_by('-fecha'),
        'reporte_productos': reporte_productos,
        'fecha_inicio': fecha_inicio_str,
        'fecha_fin': fecha_fin_str,
        'filtro': filtro_rapido,
        'cajas_recientes': cajas_recientes,
        'sesion_filtrada': sesion_filtrada
    })

@login_required
def gestion_inventario(request):
    # Seguridad
    if request.user.rol != 'gerente' and request.user.rol != 'admin':
        return redirect('usuarios:login')

    # Traemos todos los insumos ordenados por nombre
    insumos = Insumo.objects.all().order_by('nombre')
    
    # Calcular Valor Total del Inventario y por Ítem
    valor_total_inventario = 0
    for i in insumos:
        i.valor_total = i.stock_actual * i.costo_unitario
        valor_total_inventario += i.valor_total
    
    return render(request, 'usuarios/gestion_inventario.html', {
        'insumos': insumos, 
        'valor_total_inventario': valor_total_inventario
    })
# 5. PASSWORD RESET REQUEST (solicitar reseteo con EMAIL)
def password_reset_request(request):
    if request.method == 'POST':
        identifier = request.POST.get('identifier')
        
        try:
            # Buscar usuario por username o email
            user = Usuario.objects.get(Q(username=identifier) | Q(email=identifier))
            
            # Generar token
            from django.contrib.auth.tokens import default_token_generator
            from django.utils.http import urlsafe_base64_encode
            from django.utils.encoding import force_bytes
            from django.core.mail import send_mail
            from django.conf import settings
            
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Crear el link de reseteo
            reset_link = request.build_absolute_uri(
                f'/usuarios/password-reset-confirm/{uid}/{token}/'
            )
            
            # Enviar email
            subject = 'Recuperación de Contraseña - Restaurante'
            message = f'''
Hola {user.username},

Recibimos una solicitud para restablecer tu contraseña.

Haz clic en el siguiente enlace para crear una nueva contraseña:
{reset_link}

Si no solicitaste este cambio, puedes ignorar este mensaje.

Saludos,
Equipo del Restaurante
            '''
            
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
                messages.success(request, f'Se ha enviado un correo a {user.email} con las instrucciones para restablecer tu contraseña.')
            except Exception as e:
                messages.error(request, f'Error al enviar el correo: {str(e)}')
                
        except Usuario.DoesNotExist:
            # Por seguridad, mostramos el mismo mensaje aunque el usuario no exista
            messages.success(request, 'Si el usuario existe, recibirás un correo con las instrucciones.')
    
    return render(request, 'usuarios/password_reset.html')

# 6. PASSWORD RESET CONFIRM (cambiar contraseña)
def password_reset_confirm(request, uidb64, token):
    from django.utils.http import urlsafe_base64_decode
    from django.contrib.auth.tokens import default_token_generator
    
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Usuario.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, Usuario.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            if new_password and confirm_password:
                if len(new_password) < 6:
                    messages.error(request, 'La contraseña debe tener al menos 6 caracteres.')
                elif new_password == confirm_password:
                    user.set_password(new_password)
                    user.save()
                    messages.success(request, '¡Contraseña cambiada exitosamente! Ya puedes iniciar sesión.')
                    return redirect('usuarios:login')
                else:
                    messages.error(request, 'Las contraseñas no coinciden.')
            else:
                messages.error(request, 'Por favor completa ambos campos.')
        
        return render(request, 'usuarios/password_reset_confirm.html', {'validlink': True, 'user': user})
    else:
        messages.error(request, 'El enlace de reseteo es inválido o ha expirado.')
        return render(request, 'usuarios/password_reset_confirm.html', {'validlink': False})
@login_required
@user_passes_test(es_gerente)
def crear_usuario(request):
    if request.method == 'POST':
        form = CrearUsuarioForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuario creado exitosamente.')
            return redirect('usuarios:lista_usuarios')
    else:
        form = CrearUsuarioForm(user=request.user)
    
    return render(request, 'usuarios/crear_usuario.html', {'form': form})

@login_required
@user_passes_test(es_gerente)
def editar_usuario(request, usuario_id):
    usuario_editar = get_object_or_404(Usuario, pk=usuario_id)
    if request.method == 'POST':
        form = EditarUsuarioForm(request.POST, instance=usuario_editar, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuario actualizado correctamente.')
            return redirect('usuarios:lista_usuarios')
    else:
        form = EditarUsuarioForm(instance=usuario_editar, user=request.user)
    
    return render(request, 'usuarios/editar_usuario.html', {'form': form, 'usuario': usuario_editar})

@login_required
def agenda_pedidos(request):
    if not es_gerente(request.user):
        return redirect('usuarios:login')
        
    return render(request, 'usuarios/agenda.html')


# ============================================================================
# CONFIGURACIÓN DE IMPRESORAS (Panel Gerente)
# ============================================================================

@login_required
def configuracion_impresoras(request):
    if not es_gerente(request.user):
        return redirect('usuarios:login')

    from printer.models import Printer, PrinterSettings, PrintJob
    import requests as http_requests

    printer_settings = PrinterSettings.get_settings()
    printers = Printer.objects.filter(is_active=True).order_by('name')
    print_jobs = PrintJob.objects.all().order_by('-created_at')[:20]

    if request.method == 'POST':
        # Configuración global
        auto_print_kitchen = request.POST.get('auto_print_kitchen') == 'on'
        auto_print_receipt = request.POST.get('auto_print_receipt') == 'on'
        auto_open_drawer = request.POST.get('auto_open_drawer') == 'on'
        receipt_header = request.POST.get('receipt_header', '')
        receipt_footer = request.POST.get('receipt_footer', '')

        printer_settings.auto_print_kitchen = auto_print_kitchen
        printer_settings.auto_print_receipt = auto_print_receipt
        printer_settings.auto_open_drawer_on_payment = auto_open_drawer
        if receipt_header:
            printer_settings.receipt_header = receipt_header
        if receipt_footer:
            printer_settings.receipt_footer = receipt_footer
        printer_settings.save()

        # Impresora cocina
        kitchen_printer_id = request.POST.get('kitchen_printer')
        if kitchen_printer_id:
            p = Printer.objects.filter(id=kitchen_printer_id).first()
            if p:
                for printer in Printer.objects.filter(is_active=True):
                    cfg = printer.config or {}
                    cfg['prints_command'] = str(printer.id) == str(kitchen_printer_id)
                    printer.config = cfg
                    printer.save()

        # Impresora factura
        receipt_printer_id = request.POST.get('receipt_printer')
        if receipt_printer_id:
            p = Printer.objects.filter(id=receipt_printer_id).first()
            if p:
                for printer in Printer.objects.filter(is_active=True):
                    cfg = printer.config or {}
                    cfg['prints_receipt'] = str(printer.id) == str(receipt_printer_id)
                    printer.config = cfg
                    printer.save()

        messages.success(request, 'Configuración de impresión guardada correctamente.')
        return redirect('usuarios:configuracion_impresoras')

    kitchen_printer = None
    receipt_printer = None
    for p in printers:
        cfg = p.config or {}
        if cfg.get('prints_command'):
            kitchen_printer = p
        if cfg.get('prints_receipt'):
            receipt_printer = p

    context = {
        'printer_settings': printer_settings,
        'printers': printers,
        'kitchen_printer': kitchen_printer,
        'receipt_printer': receipt_printer,
        'print_jobs': print_jobs,
    }
    return render(request, 'usuarios/configuracion_impresoras.html', context)


@login_required
@require_POST
def impresora_test_print(request, printer_id):
    if not es_gerente(request.user):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    from printer.models import Printer
    from printer.print_manager import PrinterManager
    printer = get_object_or_404(Printer, id=printer_id, is_active=True)
    success, message = PrinterManager.print_test_page(printer, user=request.user.username)
    return JsonResponse({'success': success, 'message': message})


@login_required
@require_POST
def impresora_test_drawer(request, printer_id):
    if not es_gerente(request.user):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    from printer.models import Printer
    from printer.print_manager import PrinterManager
    printer = get_object_or_404(Printer, id=printer_id, is_active=True)
    success, message = PrinterManager.open_cash_drawer(printer)
    return JsonResponse({'success': success, 'message': message})


@login_required
@require_POST
def print_job_retry(request, job_id):
    if not es_gerente(request.user):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    from printer.models import PrintJob
    job = get_object_or_404(PrintJob, id=job_id)
    if job.status != 'failed':
        return JsonResponse({'error': 'Solo se pueden reintentar trabajos fallidos'}, status=400)
    job.status = 'pending'
    job.error_message = ''
    job.save(update_fields=['status', 'error_message'])
    return JsonResponse({'success': True, 'message': 'Trabajo re-enviado para impresión'})


@login_required
@require_POST
def crear_impresora(request):
    if not es_gerente(request.user):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    from printer.models import Printer
    name = request.POST.get('name', '').strip()
    printer_type = request.POST.get('printer_type', 'thermal')
    connection_type = request.POST.get('connection_type', 'usb')
    connection_string = request.POST.get('connection_string', '').strip()
    port = request.POST.get('port') or None
    paper_width = int(request.POST.get('paper_width', 80))
    is_for_kitchen = request.POST.get('is_for_kitchen') == 'on'
    is_for_receipt = request.POST.get('is_for_receipt') == 'on'

    if not name or not connection_string:
        messages.error(request, 'Nombre y dirección de conexión son obligatorios.')
        return redirect('usuarios:configuracion_impresoras')

    config = {}
    if is_for_kitchen:
        config['prints_command'] = True
    if is_for_receipt:
        config['prints_receipt'] = True

    Printer.objects.create(
        name=name,
        printer_type=printer_type,
        connection_type=connection_type,
        connection_string=connection_string,
        port=int(port) if port else None,
        paper_width=paper_width,
        characters_per_line=42 if paper_width >= 80 else 32,
        is_active=True,
        config=config
    )
    messages.success(request, f'Impresora "{name}" creada correctamente.')
    return redirect('usuarios:configuracion_impresoras')
