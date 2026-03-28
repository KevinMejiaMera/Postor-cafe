from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
from .models import Habitacion, Reserva, Huesped, TipoHabitacion

from core.decorators import gerente_required
from django.http import HttpResponse
from .models import Habitacion, Reserva, Huesped, TipoHabitacion, SesionCajaHostal
from caja.models import Gasto
from django.db.models import Sum, Count

@login_required
@gerente_required
def dashboard_hostal(request):
    habitaciones = Habitacion.objects.all().order_by('numero')
    tipos = TipoHabitacion.objects.all()

    # Calcular KPIs
    ocupadas = habitaciones.filter(estado='ocupada').count()
    total = habitaciones.count()
    ocupacion_pct = int((ocupadas / total) * 100) if total > 0 else 0

    # Entradas/Salidas Hoy
    hoy = timezone.now().date()
    entradas = Reserva.objects.filter(fecha_checkin__date=hoy).count()
    salidas  = Reserva.objects.filter(fecha_checkout__date=hoy).count()

    # Verificar si hay caja abierta
    caja_abierta = SesionCajaHostal.objects.filter(usuario=request.user, estado=True).first()

    context = {
        'habitaciones': habitaciones,
        'tipos': tipos,
        'ocupacion_pct': ocupacion_pct,
        'entradas': entradas,
        'salidas': salidas,
        'caja_abierta': caja_abierta,
    }
    return render(request, 'hostal/dashboard_hostal.html', context)

@login_required
@gerente_required
def crear_habitacion(request):
    if request.method == 'POST':
        numero     = request.POST.get('numero')
        tipo_id    = request.POST.get('tipo')
        piso       = request.POST.get('piso')
        precio_input = request.POST.get('precio')
        descripcion = request.POST.get('descripcion', '')
        
        # Validar si ya existe
        if Habitacion.objects.filter(numero=numero).exists():
            messages.error(request, f'La habitación {numero} ya existe.')
            return redirect('hostal:gestion_habitaciones')
        
        if not precio_input:
            messages.error(request, 'El precio por persona es obligatorio.')
            return redirect('hostal:gestion_habitaciones')
        
        try:
            tipo = get_object_or_404(TipoHabitacion, id=tipo_id)
            
            Habitacion.objects.create(
                numero=numero,
                tipo=tipo,
                piso=piso,
                precio_personalizado=float(precio_input),
                descripcion=descripcion,
                estado='disponible'
            )
            messages.success(request, f'Habitación {numero} creada correctamente por ${precio_input}/persona.')
        except Exception as e:
            messages.error(request, f'Error al crear habitación: {str(e)}')
            
    return redirect('hostal:gestion_habitaciones')

@login_required
@gerente_required
def crear_tipo_habitacion(request):
    """Crea un nuevo TipoHabitacion con precio por persona."""
    if request.method == 'POST':
        nombre      = request.POST.get('nombre', '').strip()
        capacidad   = request.POST.get('capacidad_personas', 1)
        descripcion = request.POST.get('descripcion', '')
        precio_persona = request.POST.get('precio_persona', 0)

        if nombre:
            TipoHabitacion.objects.create(
                nombre=nombre,
                precio_persona=float(precio_persona or 0),
                capacidad_personas=int(capacidad),
                descripcion=descripcion
            )
            messages.success(request, f'Tipo "{nombre}" creado correctamente.')
        else:
            messages.error(request, 'El nombre del tipo es obligatorio.')
    return redirect('hostal:gestion_habitaciones')

@login_required
@gerente_required
def procesar_checkin(request):
    # Verificar Caja Obligatoria
    caja = SesionCajaHostal.objects.filter(usuario=request.user, estado=True).first()
    if not caja:
        messages.error(request, 'Debe abrir la CAJA del hostal antes de realizar un Check-In.')
        return redirect('hostal:caja_hostal')

    if request.method == 'POST':
        try:
            hab_id = request.POST.get('habitacion_id')
            doc = request.POST.get('documento')
            nombre = request.POST.get('nombre_completo')
            noches = int(request.POST.get('noches', 1))
            personas = int(request.POST.get('personas', 1))
            
            habitacion = get_object_or_404(Habitacion, id=hab_id)
            
            if habitacion.estado != 'disponible':
                messages.error(request, 'La habitación ya no está disponible.')
                return redirect('hostal:dashboard_hostal')

            # 1. Crear/Buscar Huesped
            huesped, created = Huesped.objects.get_or_create(
                documento_identidad=doc,
                defaults={'nombre_completo': nombre}
            )
            
            # 2. Calcular Fechas y Precios
            checkin = timezone.now()
            checkout = checkin + timedelta(days=noches)

            # USAR precio_actual de la habitación (precio por persona)
            precio_persona_final = float(habitacion.precio_actual)

            # Si el formulario envía un precio manual, tiene prioridad
            precio_manual = request.POST.get('precio_manual')
            if precio_manual and precio_manual.strip():
                try:
                    precio_persona_final = float(precio_manual)
                except ValueError:
                    pass

            # Cobro por PERSONA (no por noche como antes)
            total = precio_persona_final * personas
            
            # 3. Crear Reserva
            reserva = Reserva.objects.create(
                huesped=huesped,
                habitacion=habitacion,
                fecha_checkin=timezone.now(),
                fecha_checkout=timezone.now() + timezone.timedelta(days=noches),
                cantidad_personas=personas,
                precio_total=total,
                pagado=total,
                estado='checkin',
                usuario=request.user
            )
            
            # 4. Actualizar Habitación
            habitacion.estado = 'ocupada'
            habitacion.save()
            
            messages.success(request, f'Check-In exitoso. Habitación {habitacion.numero} ocupada por {nombre}.')
            
        except Exception as e:
            messages.error(request, f"Error al procesar check-in: {str(e)}")
            
    return redirect('hostal:dashboard_hostal')

@login_required
@gerente_required
def calendario_reservas(request):
    year = int(request.GET.get('year', timezone.now().year))
    month = int(request.GET.get('month', timezone.now().month))
    
    # Calcular días del mes
    import calendar
    from datetime import date
    _, num_days = calendar.monthrange(year, month)
    
    days_data = []
    hoy = timezone.now().date()
    
    # Nombres de días en español
    dias_semana = ['LUN', 'MAR', 'MIÉ', 'JUE', 'VIE', 'SÁB', 'DOM']
    
    for d in range(1, num_days + 1):
        fecha_actual = date(year, month, d)
        es_hoy = (fecha_actual == hoy)
        es_finde = (fecha_actual.weekday() >= 5) # 5=Sat, 6=Sun
        
        days_data.append({
            'num': d,
            'name': dias_semana[fecha_actual.weekday()],
            'is_today': es_hoy,
            'is_weekend': es_finde,
            'full_date': fecha_actual
        })
    
    # Obtener reservas que se solapan con este mes
    import calendar
    from datetime import date
    
    habitaciones = Habitacion.objects.all().order_by('numero')
    import calendar
    from datetime import date
    
    first_day = date(year, month, 1)
    last_day = date(year, month, num_days)
    
    reservas_qs = Reserva.objects.filter(
        fecha_checkin__lte=last_day,
        fecha_checkout__gte=first_day
    ).exclude(estado__in=['cancelada', 'checkout']).select_related('huesped', 'habitacion')
    
    # Estructura para fácil acceso en template: { hab_id: [eventos] }
    eventos_por_habitacion = {}
    
    for hab in habitaciones:
        eventos_por_habitacion[hab.id] = []
        
    for res in reservas_qs:
        # Calcular inicio y fin visual (limitado al mes actual)
        start_date = res.fecha_checkin.date()
        end_date = res.fecha_checkout.date()
        
        # Ajustar bordes
        visible_start = max(start_date, first_day)
        visible_end = min(end_date, last_day)
        
        # Calcular posición (1-based para CSS grid o calc)
        start_day_num = visible_start.day
        duration_days = (visible_end - visible_start).days + 1
        
        # Determine Color based on Status
        if res.estado == 'checkin':
            color = '#8B5CF6' # Purple (Active)
        elif res.estado == 'checkout':
            color = '#9CA3AF' # Gray (History)
        else:
            color = '#F59E0B' # Orange (Pending)

        evento = {
            'id': res.id,
            'huesped': res.huesped.nombre_completo,
            'start_day': start_day_num,
            'duration': duration_days,
            'color': color,
            'status': res.estado,
            'cancellable': res.estado != 'checkout'
        }
        
        if res.habitacion_id in eventos_por_habitacion:
            eventos_por_habitacion[res.habitacion_id].append(evento)
    
    context = {
        'habitaciones': habitaciones,
        'eventos_por_habitacion': eventos_por_habitacion, # Nueva estructura
        'year': year,
        'month': month,
        'days': days_data,
        'month_name': calendar.month_name[month],
    }
    return render(request, 'hostal/calendario_reservas.html', context)

@login_required
@gerente_required
def crear_reserva(request):
    # Verificar Caja Obligatoria
    caja = SesionCajaHostal.objects.filter(usuario=request.user, estado=True).first()
    if not caja:
        messages.error(request, 'Debe abrir la CAJA del hostal antes de crear reservas.')
        return redirect('hostal:caja_hostal')

    if request.method == 'POST':
        try:
            # Guest Info
            nombre = request.POST.get('nombre_completo')
            doc = request.POST.get('documento')
            email = request.POST.get('email')
            telefono = request.POST.get('telefono')
            
            # Stay Details
            checkin_str = request.POST.get('fecha_checkin')
            checkout_str = request.POST.get('fecha_checkout')
            habitacion_id = request.POST.get('habitacion_id')
            tipo_id = request.POST.get('tipo_habitacion')
            tipo_id = request.POST.get('tipo_habitacion')
            personas = int(request.POST.get('cantidad_personas', 1))
            precio_manual = request.POST.get('precio_manual')

            # Fechas
            from django.utils.dateparse import parse_date
            checkin = parse_date(checkin_str)
            checkout = parse_date(checkout_str)
            
            if not checkin or not checkout:
                raise ValueError("Fechas inválidas")
                
            # Buscar o Crear Huesped
            huesped, created = Huesped.objects.get_or_create(
                documento_identidad=doc,
                defaults={
                    'nombre_completo': nombre,
                    'email': email,
                    'telefono': telefono
                }
            )
            if not created:
                # Update info if exists
                huesped.nombre_completo = nombre
                huesped.email = email
                huesped.telefono = telefono
                huesped.save()

            # Asignar Habitación
            habitacion = None
            if habitacion_id:
                habitacion = get_object_or_404(Habitacion, id=habitacion_id)
                # Validar disponibilidad (simple check for now)
                if habitacion.estado != 'disponible':
                    # TODO: Mejorar validación con fechas reales
                    messages.warning(request, f"La habitación {habitacion.numero} figura como {habitacion.estado}, pero se forza la reserva.")
            elif tipo_id:
                # Auto-assign available room of this type
                # Esto es simple: busca la primera disponible. 
                # En un sistema real, chequearía solapamiento de fechas.
                habitacion = Habitacion.objects.filter(tipo_id=tipo_id, estado='disponible').first()
                if not habitacion:
                     messages.error(request, "No hay habitaciones disponibles de este tipo actualmente.")
                     return redirect('hostal:crear_reserva')
            
            if not habitacion:
                raise ValueError("Debe seleccionar una habitación o tipo válido.")

            # Calculate Total (PER PERSON)
            precio_persona_final = float(habitacion.precio_actual)

            # Si el formulario envía un precio manual, tiene prioridad
            if precio_manual and precio_manual.strip():
                try:
                    precio_persona_final = float(precio_manual)
                except ValueError:
                    pass

            total = precio_persona_final * personas

            # Create Reserva
            estado_reserva = 'pendiente'
            
            # Check if reservation is for TODAY => Auto Check-In
            from django.utils import timezone
            hoy = timezone.now().date()
            
            if checkin == hoy:
                estado_reserva = 'checkin'
                habitacion.estado = 'ocupada'
                habitacion.save()
                msg_success = f"Check-In realizado automáticamente para {nombre} en Hab. {habitacion.numero}"
            else:
                msg_success = f"Reserva confirmada para el {checkin} en Hab. {habitacion.numero}"

            reserva = Reserva.objects.create(
                huesped=huesped,
                habitacion=habitacion,
                fecha_checkin=checkin,
                fecha_checkout=checkout,
                cantidad_personas=personas,
                estado=estado_reserva,
                precio_total=total
            )

            messages.success(request, msg_success)
            return redirect('hostal:dashboard_hostal')

        except Exception as e:
            messages.error(request, f"Error al crear reserva: {str(e)}")
            return redirect('hostal:crear_reserva')

    # GET Request
    habitaciones = Habitacion.objects.all().order_by('numero')
    tipos = TipoHabitacion.objects.all()
    return render(request, 'hostal/crear_reserva.html', {
        'habitaciones': habitaciones,
        'tipos': tipos
    })

@login_required
@gerente_required
def cancelar_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)
    
    if reserva.estado == 'checkin':
        messages.error(request, 'No se puede cancelar una reserva en curso (Check-In). Debe realizar el Check-Out.')
    elif reserva.estado == 'checkout':
        messages.error(request, 'Esta reserva ya finalizó.')
    else:
        # Pendiente o confirmada
        reserva.estado = 'cancelada'
        reserva.save()
        messages.success(request, 'Reserva cancelada correctamente.')
        
    return redirect(request.META.get('HTTP_REFERER', 'hostal:calendario_reservas'))

@login_required
@gerente_required
def realizar_checkout(request, habitacion_id):
    habitacion = get_object_or_404(Habitacion, id=habitacion_id)
    reserva = habitacion.reserva_actual
    
    if reserva:
        reserva.estado = 'checkout'
        reserva.save()
        
    habitacion.estado = 'limpieza'
    habitacion.save()
    
    messages.success(request, f'Check-Out realizado para la habitación {habitacion.numero}. Ahora está en limpieza.')
    return redirect('hostal:dashboard_hostal')

@login_required
@gerente_required
def finalizar_limpieza(request, habitacion_id):
    habitacion = get_object_or_404(Habitacion, id=habitacion_id)
    habitacion.estado = 'disponible'
    habitacion.save()
    
    messages.success(request, f'Habitación {habitacion.numero} habilitada y disponible.')
    return redirect('hostal:dashboard_hostal')

@login_required
@gerente_required
def finanzas_hostal(request):
    from django.db.models import Sum, Count
    from django.db.models.functions import TruncMonth
    
    hoy = timezone.now().date()
    mes_actual = hoy.month
    anio_actual = hoy.year
    
    # Base Query: Reservas activas o finalizadas (excluir canceladas)
    reservas = Reserva.objects.exclude(estado='cancelada')
    
    # 1. Ingresos Hoy (Check-ins creados hoy)
    q_hoy = reservas.filter(created_at__date=hoy).aggregate(
        total=Sum('precio_total'), 
        cant=Count('id')
    )
    total_hoy = float(q_hoy['total'] or 0)
    
    # 2. Reservas Activas (hospedados actualmente)
    reservas_activas = int(Reserva.objects.filter(estado='checkin').count())
    
    # 3. Huéspedes Hoy (Suma de personas en reservas de hoy)
    huespedes_hoy = int(reservas.filter(created_at__date=hoy).aggregate(
        total_h=Sum('cantidad_personas')
    )['total_h'] or 0)
    
    # 4. Listado Reciente (Últimas 50) con el usuario incluido
    ultimas_reservas = reservas.select_related('huesped', 'habitacion', 'usuario').order_by('-created_at')[:50]
    
    context = {
        'total_hoy': total_hoy,
        'reservas_activas': reservas_activas,
        'huespedes_hoy': huespedes_hoy,
        'ultimas_reservas': ultimas_reservas,
        'hoy': hoy,
    }
    return render(request, 'hostal/finanzas.html', context)

@login_required
@gerente_required
def gestion_habitaciones(request):
    if request.method == 'POST':
        habitacion_id = request.POST.get('habitacion_id')
        habitacion = get_object_or_404(Habitacion, id=habitacion_id)
        
        # Actualizar Estado
        nuevo_estado = request.POST.get('estado')
        if nuevo_estado in dict(Habitacion.ESTADOS):
            habitacion.estado = nuevo_estado
        
        # Actualizar Descripción
        descripcion = request.POST.get('descripcion')
        if descripcion is not None:
            habitacion.descripcion = descripcion

        # Actualizar Precio Personalizado
        precio_input = request.POST.get('precio')
        if precio_input:
            try:
                habitacion.precio_personalizado = float(precio_input)
            except ValueError:
                pass
        else:
            habitacion.precio_personalizado = None # Reset to type price if empty
            
        habitacion.save()
        messages.success(request, f'Habitación {habitacion.numero} actualizada correctamente.')
        return redirect('hostal:gestion_habitaciones')

    habitaciones = Habitacion.objects.all().order_by('numero')
    tipos = TipoHabitacion.objects.all()
    return render(request, 'hostal/gestion_habitaciones.html', {
        'habitaciones': habitaciones,
        'tipos': tipos,
    })

@login_required
@gerente_required
def modal_nueva_reserva(request):
    """Devuelve el HTML del modal de nueva reserva para HTMX."""
    # Verificar caja antes de siquiera mostrar el modal
    caja = SesionCajaHostal.objects.filter(usuario=request.user, estado=True).first()
    if not caja:
        return HttpResponse('<div class="hostal-overlay" onclick="cerrarHostalModal()"><div class="hostal-modal p-4 text-center"><h3>Caja Cerrada</h3><p>Abra la caja del hostal para continuar.</p><button class="btn btn-primary" onclick="cerrarHostalModal()">Entendido</button></div></div>')

    habitaciones = Habitacion.objects.filter(estado='disponible').order_by('numero')
    tipos = TipoHabitacion.objects.all()
    return render(request, 'hostal/modals/modal_nueva_reserva.html', {
        'habitaciones': habitaciones,
        'tipos': tipos,
    })


@login_required
@gerente_required
def caja_hostal(request):
    """Gestión de la caja del hostal. Completamente separada del restaurante."""
    caja_abierta = SesionCajaHostal.objects.filter(usuario=request.user, estado=True).first()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'abrir':
            monto = request.POST.get('monto_inicial')
            SesionCajaHostal.objects.create(usuario=request.user, monto_inicial=monto)
            messages.success(request, 'Caja del hostal aperturada correctamente.')
            return redirect('hostal:caja_hostal')

        elif action == 'cerrar' and caja_abierta:
            dinero_fisico = float(request.POST.get('monto_fisico', 0))
            # Ingresos del hostal desde apertura = reservas creadas en ese periodo
            ventas_sistema = Reserva.objects.filter(
                created_at__gte=caja_abierta.fecha_apertura
            ).exclude(estado='cancelada').aggregate(total=Sum('precio_total'))['total'] or 0

            # Gastos vinculados a esta sesión de hostal
            gastos_caja = caja_abierta.gastos_hostal.aggregate(Sum('monto'))['monto__sum'] or 0

            caja_abierta.monto_final_sistema = ventas_sistema
            caja_abierta.monto_final_fisico = dinero_fisico
            
            efectivo_esperado = float(caja_abierta.monto_inicial) + float(ventas_sistema) - float(gastos_caja)
            caja_abierta.diferencia = float(dinero_fisico) - efectivo_esperado
            caja_abierta.fecha_cierre = timezone.now()
            caja_abierta.estado = False
            caja_abierta.save()
            messages.success(request, f'Caja cerrada. Diferencia: ${caja_abierta.diferencia:.2f}')
            return redirect('hostal:caja_hostal')

    historial = SesionCajaHostal.objects.all().order_by('-fecha_apertura')[:20]

    ventas_actuales = 0
    gastos_actuales = 0
    saldo_actual = 0
    if caja_abierta:
        ventas_actuales = Reserva.objects.filter(
            created_at__gte=caja_abierta.fecha_apertura
        ).exclude(estado='cancelada').aggregate(total=Sum('precio_total'))['total'] or 0
        
        gastos_actuales = caja_abierta.gastos_hostal.aggregate(Sum('monto'))['monto__sum'] or 0
        saldo_actual = float(caja_abierta.monto_inicial) + float(ventas_actuales) - float(gastos_actuales)

    return render(request, 'hostal/caja_hostal.html', {
        'caja_abierta': caja_abierta,
        'historial': historial,
        'ventas_actuales': ventas_actuales,
        'gastos_actuales': gastos_actuales,
        'saldo_actual': saldo_actual
    })


@login_required
@gerente_required
def reportes_hostal(request):
    """Reportes de ingresos del hostal por período (separados del restaurante)."""
    from datetime import date, timedelta
    from django.utils.dateparse import parse_date

    hoy = timezone.now().date()
    filtro = request.GET.get('filtro', '')
    fecha_inicio_str = request.GET.get('fecha_inicio')
    fecha_fin_str = request.GET.get('fecha_fin')

    reservas_base = Reserva.objects.exclude(estado='cancelada').select_related('huesped', 'habitacion')
    cajas_recientes = SesionCajaHostal.objects.all().order_by('-fecha_apertura')[:10]
    sesion_filtrada = None

    if filtro == 'hoy':
        reservas = reservas_base.filter(created_at__date=hoy)
    elif filtro == 'ayer':
        reservas = reservas_base.filter(created_at__date=hoy - timedelta(days=1))
    elif filtro == 'semana':
        reservas = reservas_base.filter(created_at__date__gte=hoy - timedelta(days=7))
    elif filtro.startswith('caja_'):
        caja_id = int(filtro.split('_')[1])
        sesion_filtrada = SesionCajaHostal.objects.filter(id=caja_id).first()
        if sesion_filtrada:
            reservas = reservas_base.filter(created_at__gte=sesion_filtrada.fecha_apertura)
            if sesion_filtrada.fecha_cierre:
                reservas = reservas.filter(created_at__lte=sesion_filtrada.fecha_cierre)
        else:
            reservas = reservas_base
    elif fecha_inicio_str and fecha_fin_str:
        fi = parse_date(fecha_inicio_str)
        ff = parse_date(fecha_fin_str)
        reservas = reservas_base.filter(created_at__date__gte=fi, created_at__date__lte=ff)
    else:
        reservas = reservas_base

    total_ingresos = reservas.aggregate(total=Sum('precio_total'))['total'] or 0
    cantidad_reservas = reservas.count()

    # --- REPORTE DE "PRODUCTOS" (SERVICIOS) PARA EL HOSTAL ---
    # Convertimos las reservas en un formato similar al restaurante (Item, Cantidad, Precio, Total)
    reporte_servicios = reservas.values('habitacion__tipo__nombre').annotate(
        cantidad_vendida=Count('id'),
        total_servicio=Sum('precio_total')
    ).order_by('-cantidad_vendida')
    
    # --- PROCESAR GASTOS (NUEVO) ---

    gastos_query = Gasto.objects.filter(modulo='hostal')
    if sesion_filtrada:
        if sesion_filtrada.fecha_cierre:
             gastos_query = gastos_query.filter(fecha__gte=sesion_filtrada.fecha_apertura, fecha__lte=sesion_filtrada.fecha_cierre)
        else:
             gastos_query = gastos_query.filter(fecha__gte=sesion_filtrada.fecha_apertura)
    elif fecha_inicio_str and fecha_fin_str:
        gastos_query = gastos_query.filter(fecha__date__range=[fi, ff])
    
    total_gastos = gastos_query.aggregate(Sum('monto'))['monto__sum'] or 0
    ganancia_neta = float(total_ingresos) - float(total_gastos)

    return render(request, 'hostal/reportes_hostal.html', {
        'reservas': reservas.order_by('-created_at')[:100],
        'total_ingresos': total_ingresos,
        'total_gastos': total_gastos,
        'ganancia_neta': ganancia_neta,
        'detalles_gastos': gastos_query.order_by('-fecha'),
        'reporte_servicios': reporte_servicios,
        'cantidad_reservas': cantidad_reservas,

        'filtro': filtro,
        'fecha_inicio': fecha_inicio_str or '',
        'fecha_fin': fecha_fin_str or '',
        'cajas_recientes': cajas_recientes,
        'sesion_filtrada': sesion_filtrada,
        'hoy': hoy,
    })

# --- GESTIÓN DE RESERVAS (ELIMINAR, EDITAR, DETALLE) ---

@login_required
@gerente_required
def detalle_reserva_modal(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)
    return render(request, 'hostal/modals/modal_detalle_reserva.html', {'reserva': reserva})

@login_required
@gerente_required
def editar_reserva_modal(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)
    habitaciones = Habitacion.objects.all().order_by('numero')
    # Precios de sugerencia
    precio_actual = reserva.habitacion.precio_actual
    
    return render(request, 'hostal/modals/modal_editar_reserva.html', {
        'reserva': reserva,
        'habitaciones': habitaciones,
        'precio_actual': precio_actual
    })

@login_required
@gerente_required
def actualizar_reserva(request, reserva_id):
    if request.method == 'POST':
        reserva = get_object_or_404(Reserva, id=reserva_id)
        habitacion_viej = reserva.habitacion
        
        try:
            # 1. Update Huesped (General Info)
            huesped = reserva.huesped
            huesped.nombre_completo = request.POST.get('nombre_completo', huesped.nombre_completo)
            huesped.email = request.POST.get('email', huesped.email)
            huesped.telefono = request.POST.get('telefono', huesped.telefono)
            huesped.save()
            
            # 2. Update Reserva Details
            from django.utils.dateparse import parse_date
            checkin_str = request.POST.get('fecha_checkin')
            checkout_str = request.POST.get('fecha_checkout')
            if checkin_str: reserva.fecha_checkin = parse_date(checkin_str)
            if checkout_str: reserva.fecha_checkout = parse_date(checkout_str)
            
            reserva.cantidad_personas = int(request.POST.get('cantidad_personas', reserva.cantidad_personas))
            reserva.precio_total = float(request.POST.get('precio_total', reserva.precio_total))
            reserva.pagado = float(request.POST.get('pagado', reserva.pagado))
            reserva.observaciones = request.POST.get('observaciones', reserva.observaciones)
            
            nuevo_estado = request.POST.get('estado')
            if nuevo_estado in dict(Reserva.ESTADOS_RESERVA):
                # Sincronizar habitación si cambia estado
                reserva.estado = nuevo_estado
                
                if nuevo_estado == 'checkout' or nuevo_estado == 'cancelada':
                    reserva.habitacion.estado = 'disponible' if nuevo_estado == 'cancelada' else 'limpieza'
                    reserva.habitacion.save()
                elif nuevo_estado == 'checkin':
                    reserva.habitacion.estado = 'ocupada'
                    reserva.habitacion.save()

            reserva.save()
            messages.success(request, f'Reserva #{reserva.id} actualizada correctamente.')
            
            # Redirect intelligently
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
            
        except Exception as e:
            messages.error(request, f"Error al actualizar reserva: {str(e)}")
            
    return redirect('hostal:finanzas_hostal')

@login_required
@gerente_required
def eliminar_reserva(request, reserva_id):
    if request.method == 'POST':
        reserva = get_object_or_404(Reserva, id=reserva_id)
        habitacion = reserva.habitacion
        
        # Si estaba ocupando la habitación, la liberamos
        if reserva.estado == 'checkin':
            habitacion.estado = 'disponible'
            habitacion.save()
        
        # Eliminar
        reserva_id_display = reserva.id
        reserva.delete()
        
        messages.success(request, f'Reserva #{reserva_id_display} eliminada permanentemente. Los datos han sido restados de las finanzas.')
        
        # Devolver señal de refresh para HTMX o redirect normal
        if request.headers.get('HX-Request'):
             return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
             
    return redirect('hostal:finanzas_hostal')
