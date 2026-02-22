from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.urls import reverse
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from .models import Evento, DetalleMenu, ItemMenajeEvento, GastoEvento, IngresoEvento, Menaje
from .forms import EventoForm, EventoCreateForm, DetalleMenuForm, CostoAdicionalForm, GastoEventoForm, IngresoEventoForm, ItemMenajeEventoForm
from pedidos.models import Producto
import math
from core.decorators import gerente_required

@login_required
@gerente_required
def dashboard_eventos(request):
    eventos = Evento.objects.all().order_by('-fecha_evento')
    return render(request, 'eventos/dashboard_eventos.html', {'eventos': eventos})

@login_required
@gerente_required
def crear_evento(request):
    if request.method == 'POST':
        form = EventoCreateForm(request.POST)
        if form.is_valid():
            evento = form.save()
            return redirect('eventos:simulador_evento', evento_id=evento.id)
    else:
        form = EventoCreateForm()
    
    return render(request, 'eventos/modals/crear_evento.html', {'form': form})

@login_required
@gerente_required
def simulador_evento(request, evento_id):
    evento = get_object_or_404(Evento, pk=evento_id)
    menu_items = evento.menu_items.all().select_related('producto')
    
    # Menaje Items
    menaje_items = evento.items_menaje.all().select_related('menaje__categoria')
    
    # Catalogos para dropdowns
    categorias_gastos = GastoEvento.CATEGORIAS
    categorias_ingresos = IngresoEvento.CATEGORIAS
    
    # MENAJE CATALOG for manual add
    all_menaje = Menaje.objects.all().order_by('categoria__nombre', 'nombre')

    context = {
        'evento': evento,
        'menu_items': menu_items,
        'menaje_items': menaje_items,
        'gastos': evento.gastos.all(),
        'ingresos': evento.ingresos.all(),
        'productos': Producto.objects.filter(disponible=True), # Para agregar platos
        'categorias_gastos': categorias_gastos,
        'categorias_ingresos': categorias_ingresos,
        'all_menaje': all_menaje,
    }
    return render(request, 'eventos/simulador_evento.html', context)

# --- HTMX / ACTIONS ---

@login_required
@gerente_required
def actualizar_evento_datos(request, evento_id):
    evento = get_object_or_404(Evento, pk=evento_id)
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        personas = request.POST.get('personas')
        tipo_servicio = request.POST.get('tipo_servicio')
        estado = request.POST.get('estado')
        fecha_evento_str = request.POST.get('fecha_evento') # "YYYY-MM-DDTHH:MM" o similar
        
        try:
            evento.nombre = nombre
            evento.personas = int(personas) if personas else evento.personas
            evento.tipo_servicio = tipo_servicio
            if estado:
                evento.estado = estado
            
            if fecha_evento_str:
                # Asumimos que viene de un input datetime-local que es bastante standard
                dt_obj = parse_datetime(fecha_evento_str)
                if dt_obj:
                    if timezone.is_naive(dt_obj):
                         dt_obj = timezone.make_aware(dt_obj)
                    evento.fecha_evento = dt_obj
                
            evento.save()
            messages.success(request, "Datos del evento actualizados correctamente.")
        except Exception as e:
            messages.error(request, f"Error al actualizar: {e}")
            
    return redirect(f"{reverse('eventos:simulador_evento', args=[evento.id])}#general")

# --- MENU ---
@login_required
@gerente_required
def agregar_plato_evento(request, evento_id):
    evento = get_object_or_404(Evento, pk=evento_id)
    if request.method == 'POST':
        producto_id = request.POST.get('producto')
        if not producto_id:
            messages.error(request, "No hay productos disponibles. Primero agrega productos en la sección de Pedidos.")
            return redirect(f"{reverse('eventos:simulador_evento', args=[evento.id])}#general")
        producto = get_object_or_404(Producto, pk=producto_id)
        
        DetalleMenu.objects.create(
            evento=evento,
            producto=producto,
            cantidad=evento.personas, 
            costo_unitario_snapshot=producto.costo_elaboracion
        )
        messages.success(request, f"'{producto.nombre}' agregado al menú.")
        return redirect(f"{reverse('eventos:simulador_evento', args=[evento.id])}#general")
    return redirect('eventos:simulador_evento', evento_id=evento.id)

@login_required
@gerente_required
def eliminar_plato_evento(request, item_id):
    item = get_object_or_404(DetalleMenu, pk=item_id)
    evento_id = item.evento.id
    item.delete()
    return redirect('eventos:simulador_evento', evento_id=evento_id)

# --- MENAJE ---

@login_required
@gerente_required
def auto_calcular_menaje(request, evento_id):
    evento = get_object_or_404(Evento, pk=evento_id)
    pax = evento.personas
    
    # Lógica Heurística para Menaje
    # Busca por nombre (case-insensitive)
    def add_or_update_menaje(nombre_search, cantidad_calc):
        matches = Menaje.objects.filter(nombre__icontains=nombre_search)
        if matches.exists():
            menaje = matches.first() # Toma el primero que coincida
            item, created = ItemMenajeEvento.objects.get_or_create(
                evento=evento,
                menaje=menaje,
                defaults={'cantidad': cantidad_calc, 'costo_unitario_snapshot': menaje.costo_alquiler}
            )
            if not created:
                item.cantidad = cantidad_calc
                item.costo_unitario_snapshot = menaje.costo_alquiler
                item.save()

    # 1. Tableros (Mesas de 10)
    mesas = (pax + 9) // 10
    add_or_update_menaje('Tablero', mesas)
    add_or_update_menaje('Mantel', mesas)
    add_or_update_menaje('Cubremantel', mesas)
    
    # 2. Sillas
    add_or_update_menaje('Silla', pax) # Si tienes sillas en BD

    # 3. Vajilla / Cristalería Individual
    add_or_update_menaje('Servilleta', pax)
    add_or_update_menaje('Plato Base', pax)
    add_or_update_menaje('Plato Fuerte', pax)
    add_or_update_menaje('Plato Pan', pax)
    add_or_update_menaje('Plato Postre', pax * 2) # Segun Excel 100 para 50
    add_or_update_menaje('Cuchara Postre', pax)
    add_or_update_menaje('Tenedor Postre', pax)
    add_or_update_menaje('Tenedor Trinchero', pax) # Asumiendo nombre
    add_or_update_menaje('Cuchillo Trinchero', pax)
    
    add_or_update_menaje('Jarras', (pax + 4) // 5) # 1 jarra cada 5
    add_or_update_menaje('Vasos', pax)
    add_or_update_menaje('Copa', pax)
    
    messages.success(request, f"Menaje recalculado para {pax} personas.")
    return redirect(f"{reverse('eventos:simulador_evento', args=[evento.id])}#menaje")

@login_required
@gerente_required
def eliminar_item_menaje(request, item_id):
    item = get_object_or_404(ItemMenajeEvento, pk=item_id)
    evento_id = item.evento.id
    item.delete()
    return redirect(f"{reverse('eventos:simulador_evento', args=[evento_id])}#menaje")

# --- FINANZAS (GASTOS E INGRESOS) ---

@login_required
@gerente_required
def agregar_gasto(request, evento_id):
    evento = get_object_or_404(Evento, pk=evento_id)
    if request.method == 'POST':
        form = GastoEventoForm(request.POST)
        if form.is_valid():
            gasto = form.save(commit=False)
            gasto.evento = evento
            gasto.save()
    return redirect(f"{reverse('eventos:simulador_evento', args=[evento.id])}#gastos")

@login_required
@gerente_required
def eliminar_gasto(request, item_id):
    item = get_object_or_404(GastoEvento, pk=item_id)
    evento_id = item.evento.id
    item.delete()
    return redirect(f"{reverse('eventos:simulador_evento', args=[evento_id])}#gastos")

@login_required
@gerente_required
def agregar_ingreso(request, evento_id):
    evento = get_object_or_404(Evento, pk=evento_id)
    if request.method == 'POST':
        form = IngresoEventoForm(request.POST)
        if form.is_valid():
            ingreso = form.save(commit=False)
            ingreso.evento = evento
            ingreso.save()
    return redirect(f"{reverse('eventos:simulador_evento', args=[evento.id])}#ingresos")

@login_required
@gerente_required
def eliminar_ingreso(request, item_id):
    item = get_object_or_404(IngresoEvento, pk=item_id)
    evento_id = item.evento.id
    item.delete()
    return redirect(f"{reverse('eventos:simulador_evento', args=[evento_id])}#ingresos")

# --- LEGACY SUPPORT ---
@login_required
@gerente_required
def agregar_costo_extra(request, evento_id):
    # Redirige o adapta a GastoEvento
    return agregar_gasto(request, evento_id)

@login_required
@gerente_required
def eliminar_costo_extra(request, item_id):
    # Si aun usas el modelo viejo, dejalo, si no, redirige
    # Por compatibilidad con URL, dejemoslo pero intentemos borrar el objeto correcto
    # (El ID chocaria si son tablas distintas, asi que mejor asumimos que el template llama a las nuevas views)
    pass


@login_required
@gerente_required
def agregar_item_menaje(request, evento_id):
    evento = get_object_or_404(Evento, pk=evento_id)
    if request.method == 'POST':
        form = ItemMenajeEventoForm(request.POST)
        if form.is_valid():
            # Check if exists to update instead of duplicate
            menaje = form.cleaned_data['menaje']
            cantidad = form.cleaned_data['cantidad']
            
            item, created = ItemMenajeEvento.objects.update_or_create(
                evento=evento,
                menaje=menaje,
                defaults={
                    'cantidad': cantidad,
                    'costo_unitario_snapshot': menaje.costo_alquiler
                }
            )
            messages.success(request, f"Menaje '{menaje.nombre}' actualizado.")
        else:
            messages.error(request, "Error al agregar menaje. Verifique los datos.")
            
    return redirect(f"{reverse('eventos:simulador_evento', args=[evento.id])}#menaje")

# --- API JSON FOR CALENDAR ---
@login_required
@gerente_required
def api_eventos(request):
    # Retorna eventos para FullCalendar
    # Mostrar TODOS los eventos menos los cancelados para debug
    eventos = Evento.objects.exclude(estado='cancelado')
    events_data = []
    
    for evento in eventos:
        color = '#F59E0B' # Amarillo (Borrador)
        if evento.estado == 'confirmado':
            color = '#10B981' # Verde
        elif evento.estado == 'finalizado':
            color = '#3B82F6' # Azul
            
        events_data.append({
            'id': f'evt_{evento.id}',
            'title': evento.nombre, # Solo nombre, detalles en el modal/card
            'start': evento.fecha_evento.isoformat(),
            'url': reverse('eventos:simulador_evento', args=[evento.id]),
            'color': color,
            'extendedProps': {
                'tipo': 'evento',
                'servicio': evento.get_tipo_servicio_display(),
                'personas': evento.personas,
                'fecha_creacion': evento.created_at.strftime("%d/%m/%Y"),
                'estado_texto': evento.get_estado_display()
            }
        })
        
    return JsonResponse(events_data, safe=False)
