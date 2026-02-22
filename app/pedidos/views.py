
# 📁 pedidos/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse
import json
from django.views.decorators.http import etag
from django.utils import timezone

from clientes.models import Cliente
from .models import Pedido, Producto, DetallePedido, Mesa, Factura
from usuarios.models import AuditLog
from usuarios.models import AuditLog
from inventario.models import MovimientoKardex, Insumo
from .forms import ProductoForm # Importar Formulario
from django.db.models import Avg, F, Count, ExpressionWrapper, DurationField
from core.decorators import mesero_required, cocina_required, gerente_required

# --- FUNCIÓN AUXILIAR PARA LA IP ---
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

# --- VISTAS DEL MESERO ---

# 👇👇👇 ESTA ES LA VISTA NUEVA QUE FALTABA 👇👇👇
@login_required
@mesero_required
def panel_mesas(request):
    # Traemos todas las mesas ordenadas por su número
    mesas = Mesa.objects.all().order_by('numero')
    return render(request, 'pedidos/panel_mesas.html', {'mesas': mesas})
# 👆👆👆 FIN DE LO NUEVO 👆👆👆

@login_required
@mesero_required
def detalle_mesa(request, mesa_id):
    mesa = get_object_or_404(Mesa, pk=mesa_id)
    
    # Buscamos si hay un pedido activo
    pedido_activo = Pedido.objects.filter(
        mesa=mesa, 
        estado__in=['borrador', 'confirmado', 'listo', 'entregado']
    ).first()
    
    # Si no hay pedido y la mesa está libre, creamos uno nuevo (pero NO ocupamos la mesa aún)
    if not pedido_activo:
        pedido_activo = Pedido.objects.create(
            mesa=mesa,
            mesero=request.user,
            estado='borrador'
        )
        # mesa.estado = 'ocupada'  <-- ELIMINADO: No ocupar hasta que haya productos
        # mesa.save()

    productos = Producto.objects.filter(disponible=True)

    # Detección manual de HTMX
    is_htmx = request.headers.get('HX-Request') == 'true' or request.META.get('HTTP_HX_REQUEST')

    context = {
        'mesa': mesa,
        'pedido': pedido_activo,
        'productos': productos,
        'is_htmx': is_htmx,
    }
    return render(request, 'pedidos/detalle_mesa.html', context)

@login_required
@mesero_required
def agregar_producto(request, pedido_id, producto_id):
    
    # 1. Buscamos los objetos con los IDs que vienen de la URL
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    producto = get_object_or_404(Producto, pk=producto_id)

    # 2. Lógica de inventario
    if producto.stock > 0:
        detalle, created = DetallePedido.objects.get_or_create(
            pedido=pedido,
            producto=producto,
            defaults={'precio_unitario': producto.precio}
        )
        
        if not created:
            detalle.cantidad += 1
            detalle.save()
        
        # Restar stock
        producto.stock -= 1
        producto.save()

        # NUEVO: Si la mesa estaba libre, ahora sí la ocupamos
        if pedido.mesa.estado == 'libre':
            pedido.mesa.estado = 'ocupada'
            pedido.mesa.save()

    # 3. Respuesta: Devolvemos el HTML del panel derecho actualizado
    context = {
        'pedido': pedido,
        'mesa': pedido.mesa
    }
    return render(request, 'pedidos/partials/orden_actual.html', context)

@login_required
@mesero_required
def confirmar_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    
    if pedido.items.exists():
        if request.method == 'POST':
            nota = request.POST.get('nota_cocina')
            if nota:
                pedido.observacion = nota

        pedido.estado = 'confirmado'
        pedido.fecha_confirmado = timezone.now() # GUARDAR LA HORA DE ENVIO
        pedido.save()
        
        # 1. LOG DE AUDITORÍA
        AuditLog.objects.create(
            user=request.user,
            ip_address=get_client_ip(request),
            action=f"Envió a cocina: Pedido #{pedido.id} (Mesa {pedido.mesa.numero})"
        )

        # 2. DESCARGA DE INVENTARIO (RECETAS)
        for detalle in pedido.items.all():
            producto = detalle.producto
            cantidad_vendida = detalle.cantidad

            if producto.receta.exists():
                for item_receta in producto.receta.all():
                    insumo = item_receta.insumo
                    cantidad_a_descontar = item_receta.cantidad_necesaria * cantidad_vendida
                    
                    # Restamos del stock del INSUMO
                    insumo.stock_actual -= cantidad_a_descontar
                    insumo.save()

                    # Guardamos en Kardex
                    MovimientoKardex.objects.create(
                        insumo=insumo,
                        tipo='salida',
                        cantidad=cantidad_a_descontar,
                        costo_total=cantidad_a_descontar * insumo.costo_unitario,
                        observacion=f"Venta Pedido #{pedido.id}: {producto.nombre} x{cantidad_vendida}"
                    )
        
        return redirect('usuarios:dashboard_mesero')
    else:
        return redirect('pedidos:detalle_mesa', mesa_id=pedido.mesa.id)

@login_required
@mesero_required
def pagar_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)

    if pedido.estado in ['confirmado', 'listo', 'entregado']:
        # 1. Marcar como pagado
        pedido.estado = 'pagado'
        pedido.save()
        
        # 2. Liberar mesa
        mesa = pedido.mesa
        mesa.estado = 'libre'
        mesa.save()

        # LOG DE AUDITORÍA
        AuditLog.objects.create(
            user=request.user,
            ip_address=get_client_ip(request),
            action=f"Cobró cuenta: Pedido #{pedido.id} - Total ${pedido.total}"
        )
    
    return redirect('usuarios:dashboard_mesero')

# --- VISTAS DE COCINA ---

@login_required
@cocina_required
def dashboard_cocina(request):

    pedidos = Pedido.objects.filter(estado='confirmado').order_by('created_at')
    return render(request, 'pedidos/dashboard_cocina.html', {'pedidos': pedidos})

@login_required
@cocina_required
def terminar_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    
    if pedido.estado == 'confirmado':
        pedido.estado = 'listo'
        pedido.fecha_listo = timezone.now() # GUARDAR LA HORA FINAL
        pedido.notificacion_vista = False   # ACTIVAR NOTIFICACIÓN
        pedido.save()

        # LOG DE AUDITORÍA
        AuditLog.objects.create(
            user=request.user,
            ip_address=get_client_ip(request),
            action=f"Cocina terminó: Pedido #{pedido.id}"
        )
    
    return redirect('pedidos:dashboard_cocina')

# --- NUEVA VISTA PARA HTMX (+/- CANTIDAD) ---

@login_required
@mesero_required
def modificar_cantidad_item(request, item_id, accion):
    # CORREGIDO: Usamos 'DetallePedido' en lugar de 'PedidoItem'
    item = get_object_or_404(DetallePedido, id=item_id)
    pedido = item.pedido
    
    if pedido.estado == 'borrador':
        if accion == 'sumar':
            item.cantidad += 1
            item.save()
        elif accion == 'restar':
            item.cantidad -= 1
            if item.cantidad <= 0:
                item.delete()
            else:
                item.save()
        
    # Devolvemos el HTML parcial para HTMX
    context = {
        'pedido': pedido,
        'mesa': pedido.mesa
    }
    return render(request, 'pedidos/partials/orden_actual.html', context)

def cocina_etag(request, *args, **kwargs):
    # Buscamos el último pedido modificado o creado
    ultimo_pedido = Pedido.objects.filter(estado='confirmado').order_by('-updated_at').first()
    conteo = Pedido.objects.filter(estado='confirmado').count()
    
    if ultimo_pedido:
        # La huella es: Cantidad de pedidos + Fecha del último cambio
        return str(conteo) + str(ultimo_pedido.updated_at)
    else:
        return "0"

# Con esto logramos que la cocina se actualice cada cierto tiempo 

@login_required
@etag(cocina_etag)
@cocina_required
def actualizar_cocina(request):
   
    # Buscamos SOLO los pedidos 'confirmado' (pendientes de cocinar)
    # Ordenamos por antigüedad (el más viejo primero)
    pedidos = Pedido.objects.filter(estado='confirmado').order_by('created_at')
    return render(request, 'pedidos/partials/lista_pedidos_cocina.html', {'pedidos': pedidos})

@login_required
@cocina_required
def ver_comanda(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    return render(request, 'pedidos/comanda_cocina.html', {'pedido': pedido, 'now': timezone.now()})

@login_required
@mesero_required
def modal_cobrar(request, pedido_id):
    # Buscamos el pedido para mostrar el total
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    return render(request, 'pedidos/modals/cobrar.html', {'pedido': pedido})

@login_required
@mesero_required
def procesar_pago(request, pedido_id):
    if request.method == 'POST':
        pedido = get_object_or_404(Pedido, pk=pedido_id)
        cliente_id = request.POST.get('cliente_id')
        
        # 1. Obtener Cliente (si enviaron uno)
        cliente = None
        if cliente_id:
            cliente = get_object_or_404(Cliente, pk=cliente_id)
            
        # 2. Crear la Factura (Snapshot de datos)
        # Si no hay cliente, usamos datos genéricos de Consumidor Final
        datos_factura = {
            'pedido': pedido,
            'cliente': cliente,
            'subtotal': pedido.total, 
            'total': pedido.total,
            'metodo_pago': 'efectivo', 
            'razon_social': cliente.nombres if cliente else 'CONSUMIDOR FINAL',
            'ruc_ci': cliente.cedula_o_ruc if cliente else '9999999999999',
            'direccion': cliente.direccion if cliente else '',
            'correo': cliente.email if cliente else ''
        }
        
        factura = Factura.objects.create(**datos_factura)
        
        # 3. AUTOMATIZACIÓN DE INVENTARIO (KARDEX)
        # Recorremos cada plato vendido para descontar sus ingredientes
        for item in pedido.items.all():
            producto = item.producto
            cantidad_vendida = item.cantidad
            
            # Buscamos si el producto tiene receta (ingredientes)
            if hasattr(producto, 'receta'):
                for ingrediente in producto.receta.all():
                    insumo = ingrediente.insumo
                    cantidad_a_descontar = ingrediente.cantidad_necesaria * cantidad_vendida
                    
                    # Registramos la salida en el Kardex
                    MovimientoKardex.objects.create(
                        insumo=insumo,
                        tipo='salida',
                        cantidad=cantidad_a_descontar,
                        costo_total=cantidad_a_descontar * insumo.costo_unitario, # Costo estimado
                        observacion=f"Venta Pedido #{pedido.id}: {cantidad_vendida}x {producto.nombre}"
                    )

        # 4. Actualizar Estados
        pedido.estado = 'pagado'
        pedido.save()
        
        mesa = pedido.mesa
        mesa.estado = 'libre'
        mesa.save()
        
        # 4. Redirigir al Ticket
        return redirect('pedidos:ver_ticket', factura_id=factura.id)

def ver_ticket(request, factura_id):
    factura = get_object_or_404(Factura, pk=factura_id)
    return render(request, 'pedidos/ticket.html', {'factura': factura})

# --- GESTIÓN DE PRODUCTOS (GERENTE) ---

# --- GESTIÓN DE RECETAS (Menú Gerente) ---
from .forms import RecetaForm 
from inventario.models import Receta

@login_required
@gerente_required
def gestion_receta(request, producto_id):
    producto = get_object_or_404(Producto, pk=producto_id)
    recetas = producto.receta.all() # Related name configurado en el modelo
    
    if request.method == 'POST':
        form = RecetaForm(request.POST)
        if form.is_valid():
            nueva_receta = form.save(commit=False)
            nueva_receta.producto = producto
            nueva_receta.save()
            
            # REFRESCAR LA LISTA DE RECETAS
            recetas = producto.receta.all()
            
            # Recargamos el mismo modal con los datos actualizados
            return render(request, 'pedidos/modals/gestion_receta.html', {
                'producto': producto, 'recetas': recetas, 'form': RecetaForm()
            })
        else:
            # Si hay error, mostramos el formulario con errores
            return render(request, 'pedidos/modals/gestion_receta.html', {
                'producto': producto, 'recetas': recetas, 'form': form
            })
    else:
        form = RecetaForm()

    return render(request, 'pedidos/modals/gestion_receta.html', {
        'producto': producto,
        'recetas': recetas,
        'form': form
    })

@login_required
@gerente_required
def eliminar_ingrediente(request, receta_id):
    receta_item = get_object_or_404(Receta, pk=receta_id)
    producto_id = receta_item.producto.id
    receta_item.delete()
    
    # Redirigimos de vuelta al modal principal de gestión de ese producto
    return gestion_receta(request, producto_id)

@login_required
@gerente_required
def crear_producto(request):

    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            # Retornar refresh para actualizar la tabla
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
    else:
        form = ProductoForm()
    
    return render(request, 'pedidos/modals/form_producto.html', {'form': form, 'titulo': 'Nuevo Plato'})

@login_required
@gerente_required
def editar_producto(request, pk):

    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
    else:
        form = ProductoForm(instance=producto)
    
    return render(request, 'pedidos/modals/form_producto.html', {'form': form, 'titulo': f'Editar {producto.nombre}'})

@login_required
@require_POST
@gerente_required
def eliminar_producto(request, pk):
    
    producto = get_object_or_404(Producto, pk=pk)
    producto.delete()
    return HttpResponse(status=204, headers={'HX-Refresh': 'true'})

@login_required
@mesero_required
def check_notificaciones(request):

    # Buscar pedidos listos que pertenezcan al mesero actual Y que no hayan sido vistos
    pedidos_listos = Pedido.objects.filter(
        mesero=request.user, 
        estado='listo',
        notificacion_vista=False
    )
    
    if not pedidos_listos.exists():
        return HttpResponse("")

    return render(request, 'pedidos/partials/notificaciones.html', {'pedidos_listos': pedidos_listos})

    return render(request, 'pedidos/partials/notificaciones.html', {'pedidos_listos': pedidos_listos})

@login_required
@mesero_required
def marcar_notificacion_vista(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    if pedido.mesero == request.user:
        pedido.notificacion_vista = True
        pedido.save()
    return HttpResponse("")

@login_required
@gerente_required
def reporte_tiempos_cocina(request):

    # 1. Reporte Histórico (Promedios)
    reporte_qs = DetallePedido.objects.filter(
        pedido__fecha_confirmado__isnull=False, 
        pedido__fecha_listo__isnull=False
    ).values(
        'producto__nombre'
    ).annotate(
        tiempo_promedio=Avg(
            ExpressionWrapper(
                F('pedido__fecha_listo') - F('pedido__fecha_confirmado'),
                output_field=DurationField()
            )
        ),
        veces_pedido=Count('id')
    ).order_by('-tiempo_promedio')
    
    # Convertir a dict para búsqueda rápida por nombre en el template
    promedios = {item['producto__nombre']: item['tiempo_promedio'] for item in reporte_qs}

    # 2. Pedidos en Curso (Monitor en Vivo)
    # Pedidos confirmados pero NO listos
    pedidos_en_curso = Pedido.objects.filter(
        estado='confirmado',
        fecha_listo__isnull=True
    ).order_by('fecha_confirmado')

    return render(request, 'pedidos/reporte_tiempos.html', {
        'reporte': reporte_qs,
        'pedidos_en_curso': pedidos_en_curso,
        'promedios_json': json.dumps({k: v.total_seconds() for k, v in promedios.items() if v}, default=str)
    })

# --- INGENIERÍA DE MENÚ (FICHA TÉCNICA) ---
from decimal import Decimal

def calcular_costo_receta(ingredientes_queryset):
    """
    Calcula el costo total de una lista de ingredientes (Receta),
    manejando recursividad si hay sub-recetas.
    Retorna: (Costo Total, Lista Detallada)
    """
    costo_total = Decimal(0)
    detalle = []
    
    for item in ingredientes_queryset:
        insumo = item.insumo
        
        # 1. Determinar Costo Unitario
        costo_unitario = insumo.costo_unitario
        es_subreceta = getattr(insumo, 'es_subreceta', False)

        # Si es SUB-RECETA, calculamos su costo real basado en SUS ingredientes
        if es_subreceta:
            sub_ingredientes = insumo.ingredientes_de_receta.all()
            if sub_ingredientes.exists():
                costo_batch, _ = calcular_costo_receta(sub_ingredientes)
                # El costo unitario es Costo Batch / Rendimiento
                rendimiento = insumo.rendimiento_receta if insumo.rendimiento_receta > 0 else 1
                costo_unitario = costo_batch / rendimiento

        costo_item = item.cantidad_necesaria * costo_unitario
        costo_total += costo_item
        
        detalle.append({
            'nombre': insumo.nombre,
            'es_subreceta': es_subreceta,
            'unidad': insumo.get_unidad_medida_display(),
            'cantidad': item.cantidad_necesaria,
            'costo_unitario': costo_unitario, # Costo Real calculado
            'costo_total': costo_item
        })

    return costo_total, detalle

@login_required
@gerente_required
def ver_ficha_tecnica(request, producto_id):
        
    producto = get_object_or_404(Producto, pk=producto_id)
    receta_qs = producto.receta.all()
    
    # Calcular Costos
    costo_materia_prima, detalle_ingredientes = calcular_costo_receta(receta_qs)
    
    # Calcular KPIs
    precio_venta = producto.precio
    # Evitar division por cero
    food_cost_pct = (costo_materia_prima / precio_venta * 100) if precio_venta > 0 else 0
    margen_contribucion = precio_venta - costo_materia_prima
    margen_pct = (margen_contribucion / precio_venta * 100) if precio_venta > 0 else 0
    
    return render(request, 'pedidos/ficha_tecnica.html', {
        'producto': producto,
        'costo_total': costo_materia_prima,
        'ingredientes': detalle_ingredientes,
        'food_cost_pct': food_cost_pct,
        'margen_contribucion': margen_contribucion,
        'margen_pct': margen_pct
    })


# --- GESTION DE SUB-RECETAS (Insumos que son Recetas) ---
@login_required
@gerente_required
def gestion_receta_insumo(request, insumo_id):
    parent_insumo = get_object_or_404(Insumo, pk=insumo_id)
    
    # Validar que sea una sub-receta
    if not parent_insumo.es_subreceta:
        return HttpResponse('Este insumo no esta marcado como Sub-receta.', status=400)

    recetas = parent_insumo.ingredientes_de_receta.all() # Related name: ingredientes_de_receta
    
    if request.method == 'POST':
        form = RecetaForm(request.POST)
        if form.is_valid():
            nueva_receta = form.save(commit=False)
            nueva_receta.insumo_principal = parent_insumo # ASIGNAMOS EL PADRE INSUMO
            nueva_receta.save()
            
            # Refrescar
            recetas = parent_insumo.ingredientes_de_receta.all()
            return render(request, 'pedidos/modals/gestion_receta_insumo.html', {
                'parent_insumo': parent_insumo, 'recetas': recetas, 'form': RecetaForm()
            })
    else:
        form = RecetaForm()

    return render(request, 'pedidos/modals/gestion_receta_insumo.html', {
        'parent_insumo': parent_insumo,
        'recetas': recetas,
        'form': form
    })

@login_required
@gerente_required
def eliminar_ingrediente_insumo(request, receta_id):
    receta_item = get_object_or_404(Receta, pk=receta_id)
    insumo_id = receta_item.insumo_principal.id
    receta_item.delete()
    return gestion_receta_insumo(request, insumo_id)

# --- API JSON FOR CALENDAR ---
@login_required
@mesero_required
def api_pedidos_agenda(request):
    # Retorna pedidos PROGRAMADOS para FullCalendar (tienen fecha_entrega)
    pedidos = Pedido.objects.filter(fecha_entrega__isnull=False).exclude(estado='cancelado')
    events_data = []
    
    for pedido in pedidos:
        titulo = f"Pedido #{pedido.id}"
        cliente_nombre = "Cliente Casual"
        
        if pedido.cliente:
            cliente_nombre = pedido.cliente.nombres
            titulo += f" - {cliente_nombre}"
        elif pedido.mesa:
            titulo += f" (Mesa {pedido.mesa.numero})"
            
        # Resumen de Items
        items_resumen = ", ".join([f"{item.cantidad}x {item.producto.nombre}" for item in pedido.items.all()])
            
        events_data.append({
            'id': f'ped_{pedido.id}',
            'title': titulo,
            'start': pedido.fecha_entrega.isoformat(),
            'url': reverse('pedidos:detalle_mesa', args=[pedido.mesa.id]) if pedido.mesa else '#',
            'color': '#FF5722', # Naranja Tomate
            'extendedProps': {
                'tipo': 'pedido',
                'estado': pedido.get_estado_display(),
                'fecha_pedido': pedido.created_at.strftime("%d/%m/%Y %H:%M"),
                'fecha_entrega': pedido.fecha_entrega.strftime("%d/%m/%Y %H:%M"),
                'cliente': cliente_nombre,
                'items': items_resumen,
                'valor': float(pedido.total)
            }
        })
        
    return JsonResponse(events_data, safe=False)

@login_required
@require_POST
@mesero_required
def crear_pedido_agendado(request):
    fecha_entrega = request.POST.get('fecha_entrega') # YYYY-MM-DDTHH:mm
    cliente_nombre = request.POST.get('nombre_cliente')
    
    # 1. Crear Cliente 'Ad-hoc' o buscar
    # Por simplicidad ahora, si no existe un sistema de clientes robusto en el frontend,
    # podríamos solo asignar el nombre a una "Nota" o crear un cliente simple.
    # Asumiremos que el frontend enviará (idealmente) un ID de cliente o creamos uno "Casual".
    
    cliente = None
    if cliente_nombre:
        # Busca o crea cliente por Nombre (Básico)
        cliente, _ = Cliente.objects.get_or_create(
            nombres=cliente_nombre,
            defaults={'cedula_o_ruc': '9999999999', 'direccion': 'Dirección Pendiente'}
        )
        
    # 2. Crear Pedido
    pedido = Pedido.objects.create(
        mesero=request.user,
        estado='borrador',
        fecha_entrega=fecha_entrega,
        cliente=cliente,
        mesa=None # Pedido de Agenda / Delivery
    )
    
    # 3. Redirigir a "Detalle Mesa" (Modificado para soportar pedidos sin mesa)
    # Como detalle_mesa requiere mesa_id, necesitamos una vista que maneje "Pedido por ID"
    # OJO: detalle_mesa actual depende FUERTE de mesa_id.
    # Estrategia Rápida: Crear una "Mesa Virtual" para la visualización o adaptar detalle_mesa.
    # Adaptaremos detalle_mesa para que si mesa_id es 0 o None, busque por pedido_id.
    # PERO la URL espera int:mesa_id.
    
    # Solución: Redirigir a una nueva vista o usar una "Mesa Virtual" 999.
    # Mejor: Crear 'editar_pedido_directo' que reutilice el template.
    
    return redirect('pedidos:editar_pedido_directo', pedido_id=pedido.id) 

@login_required
@mesero_required
def editar_pedido_directo(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    productos = Producto.objects.filter(disponible=True)
    
    # Renderizamos el template específico que no necesita mesa
    return render(request, 'pedidos/editar_pedido.html', {
        'pedido': pedido,
        'productos': productos,
        'mesa': None, # Explícito
        'is_htmx': False 
    })

