from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
from .models import Habitacion, Reserva, Huesped, TipoHabitacion

from core.decorators import gerente_required

@login_required
@gerente_required
def dashboard_hostal(request):
    habitaciones = Habitacion.objects.all().order_by('numero')
    tipos = TipoHabitacion.objects.all() # Para el modal de crear habitación
    
    # Calcular KPIs
    ocupadas = habitaciones.filter(estado='ocupada').count()
    total = habitaciones.count()
    ocupacion_pct = int((ocupadas / total) * 100) if total > 0 else 0
    
    # Entradas/Salidas Hoy (Simple query por ahora)
    hoy = timezone.now().date()
    entradas = Reserva.objects.filter(fecha_checkin__date=hoy).count()
    salidas = Reserva.objects.filter(fecha_checkout__date=hoy).count()

    context = {
        'habitaciones': habitaciones,
        'tipos': tipos,
        'ocupacion_pct': ocupacion_pct,
        'entradas': entradas,
        'salidas': salidas,
    }
    return render(request, 'hostal/dashboard_hostal.html', context)

@login_required
@gerente_required
def crear_habitacion(request):
    if request.method == 'POST':
        numero = request.POST.get('numero')
        tipo_id = request.POST.get('tipo')
        piso = request.POST.get('piso')
        precio_input = request.POST.get('precio') # Nuevo campo
        
        # Validar si ya existe
        if Habitacion.objects.filter(numero=numero).exists():
            messages.error(request, f'La habitación {numero} ya existe.')
            return redirect('hostal:dashboard_hostal')
        
        try:
            tipo = get_object_or_404(TipoHabitacion, id=tipo_id)
            
            # Limpiar precio
            precio_personalizado = None
            if precio_input and precio_input.strip():
                precio_personalizado = float(precio_input)
            
            Habitacion.objects.create(
                numero=numero,
                tipo=tipo,
                piso=piso,
                precio_personalizado=precio_personalizado,
                estado='disponible'
            )
            messages.success(request, f'Habitación {numero} creada correctamente.')
        except Exception as e:
            messages.error(request, f'Error al crear habitación: {str(e)}')
            
    return redirect('hostal:dashboard_hostal')

@login_required
@gerente_required
def procesar_checkin(request):
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
            precio_noche = habitacion.tipo.precio_noche
            
            # Lógica de Precio Manual (Interpretado como Precio por Noche según feedback)
            precio_manual = request.POST.get('precio_manual')
            precio_noche_final = habitacion.tipo.precio_noche
            
            if precio_manual and float(precio_manual) >= 0:
                precio_noche_final = float(precio_manual)
                
            total = precio_noche_final * noches
            
            # 3. Crear Reserva
            Reserva.objects.create(
                huesped=huesped,
                habitacion=habitacion,
                fecha_checkin=checkin,
                fecha_checkout=checkout,
                cantidad_personas=personas,
                estado='checkin', # Ya está hospedado
                precio_total=total,
                pagado=0 # Se paga al checkout usualmente, o checkin
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

            # Calculate Total
            noches = (checkout - checkin).days
            if noches < 1: noches = 1
            
            # Lógica de Precio: Manual (prioridad) vs Automático
            precio_noche_final = habitacion.tipo.precio_noche
            if precio_manual and float(precio_manual) >= 0:
                 precio_noche_final = float(precio_manual)
            
            total = precio_noche_final * noches

            # Create Reserva
            estado_reserva = 'pendiente'
            
            # Check if reservation is for TODAY => Auto Check-In
            from django.utils import timezone
            hoy = timezone.now().date()
            
            # Convert parsed dates to matching types for comparison if needed, 
            # though parse_date returns a date object.
            
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
    
    # 1. Ingresos Hoy (Check-ins creados hoy o cobros hoy - simplificado a fecha reserva)
    query_hoy = reservas.filter(
        created_at__date=hoy
    ).aggregate(total=Sum('precio_total'), cant=Count('id'))
    ingreso_hoy = query_hoy['total'] or 0
    cantidad_hoy = query_hoy['cant'] or 0
    
    # 2. Ingresos Mes Actual
    query_mes = reservas.filter(
        created_at__month=mes_actual,
        created_at__year=anio_actual
    ).aggregate(total=Sum('precio_total'), cant=Count('id'))
    ingreso_mes = query_mes['total'] or 0
    cantidad_mes = query_mes['cant'] or 0
    
    # 3. Listado Reciente (Últimas 50)
    ultimas_reservas = reservas.select_related('huesped', 'habitacion').order_by('-created_at')[:50]
    
    context = {
        'ingreso_hoy': ingreso_hoy,
        'cantidad_hoy': cantidad_hoy,
        'ingreso_mes': ingreso_mes,
        'cantidad_mes': cantidad_mes,
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
    return render(request, 'hostal/gestion_habitaciones.html', {'habitaciones': habitaciones})
