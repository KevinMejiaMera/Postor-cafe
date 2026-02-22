
# 📁 usuarios/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import CrearUsuarioForm, EditarUsuarioForm
from django.db.models import Q, Sum
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone 
from .models import Usuario, AuditLog
from pedidos.models import Pedido, Mesa
from pedidos.models import Producto, Factura, DetallePedido
import csv
from django.db.models.functions import TruncDay
from django.utils.dateparse import parse_date
import datetime
from django.http import HttpResponse
from pedidos.models import Pedido 
from inventario.models import Insumo

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

    # Filtros de Fecha
    fecha_inicio_str = request.GET.get('fecha_inicio')
    fecha_fin_str = request.GET.get('fecha_fin')
    
    # Query Base: Facturas (Ventas reales)
    facturas = Factura.objects.all().order_by('-fecha_emision').select_related('pedido', 'pedido__mesa', 'pedido__mesero')

    # Aplicar Filtros
    if fecha_inicio_str and fecha_fin_str:
        fecha_inicio = parse_date(fecha_inicio_str)
        fecha_fin = parse_date(fecha_fin_str)
        if fecha_inicio and fecha_fin:
            facturas = facturas.filter(fecha_emision__date__range=[fecha_inicio, fecha_fin])

    # Calcular Ingresos Totales (Usando campo real 'total' de Factura)
    total_ingresos = facturas.aggregate(Sum('total'))['total__sum'] or 0

    # Lógica de Exportación a Excel (CSV)
    if 'exportar' in request.GET:
        response = HttpResponse(content_type='text/csv')
        response.write(u'\ufeff'.encode('utf8'))
        response['Content-Disposition'] = 'attachment; filename="reporte_ventas.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['ID Factura', 'Fecha Emisión', 'Pedido ID', 'Mesa', 'Mesero', 'Cliente', 'Total'])
        
        for f in facturas:
            mesero = f.pedido.mesero.username if f.pedido.mesero else 'Desconocido'
            mesa = f"Mesa {f.pedido.mesa.numero}" if f.pedido.mesa else 'Sin Mesa'
            writer.writerow([
                f.id, 
                f.fecha_emision.strftime("%d/%m/%Y %H:%M"), 
                f.pedido.id,
                mesa, 
                mesero,
                f.razon_social, # Cliente Snapshot
                f.total
            ])
        return response

    # Agregación para Gráfico (Ventas por Día)
    ventas_diarias = facturas.annotate(dia=TruncDay('fecha_emision')).values('dia').annotate(total=Sum('total')).order_by('dia')
    
    labels_chart = [v['dia'].strftime("%d/%m") for v in ventas_diarias]
    data_chart = [float(v['total']) for v in ventas_diarias]

    return render(request, 'usuarios/reportes.html', {
        'facturas': facturas, 
        'total_ingresos': total_ingresos,
        'labels_chart': labels_chart,
        'data_chart': data_chart,
        'fecha_inicio': fecha_inicio_str,
        'fecha_fin': fecha_fin_str
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
