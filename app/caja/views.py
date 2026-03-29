from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from core.decorators import gerente_required
from django.utils import timezone
from .models import SesionCaja, Gasto

def _gestion_gastos_logica(request, modulo_fijo=None):
    from hostal.models import SesionCajaHostal
    caja_restaurante = SesionCaja.objects.filter(estado=True).first()
    caja_hostal = SesionCajaHostal.objects.filter(estado=True).first()
    
    # Determinar qué caja usar según el módulo fijo o el enviado por POST
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'crear':
            mod = modulo_fijo or request.POST.get('modulo', 'restaurante')
            
            # Verificar si hay caja abierta según el módulo
            error_msg = None
            if mod == 'restaurante' and not caja_restaurante:
                error_msg = "Error: Debe tener una caja de RESTAURANTE abierta para registrar este gasto."
            elif mod == 'hostal' and not caja_hostal:
                error_msg = "Error: Debe tener una caja de HOSTAL abierta para registrar este gasto."
            
            if error_msg:
                messages.error(request, error_msg)
            else:
                desc = request.POST.get('descripcion')
                monto = request.POST.get('monto')
                
                Gasto.objects.create(
                    descripcion=desc,
                    monto=monto,
                    usuario=request.user,
                    modulo=mod,
                    sesion_caja=caja_restaurante if mod == 'restaurante' else None,
                    sesion_caja_hostal=caja_hostal if mod == 'hostal' else None
                )
                messages.success(request, f"Gasto de ${monto} registrado correctamente en {mod.capitalize()}.")
            
            if modulo_fijo == 'restaurante':
                return redirect('caja:gestion_gastos_restaurante')
            elif modulo_fijo == 'hostal':
                return redirect('caja:gestion_gastos_hostal')
            return redirect('caja:gestion_gastos')
            
        elif action == 'eliminar':
            gasto_id = request.POST.get('gasto_id')
            gasto = get_object_or_404(Gasto, id=gasto_id)
            if gasto.usuario == request.user or request.user.rol in ['gerente', 'admin']:
                gasto.delete()
                messages.success(request, "Gasto eliminado.")
            
            if modulo_fijo == 'restaurante':
                return redirect('caja:gestion_gastos_restaurante')
            elif modulo_fijo == 'hostal':
                return redirect('caja:gestion_gastos_hostal')
            return redirect('caja:gestion_gastos')

    # Ver gastos frecuentes
    gastos = Gasto.objects.all().order_by('-fecha')
    if modulo_fijo:
        gastos = gastos.filter(modulo=modulo_fijo)
    
    if request.user.rol not in ['gerente', 'admin']:
        gastos = gastos.filter(usuario=request.user)
    
    gastos = gastos[:50]

    return render(request, 'caja/gestion_gastos.html', {
        'caja_abierta': caja_restaurante if modulo_fijo == 'restaurante' else (caja_hostal if modulo_fijo == 'hostal' else (caja_restaurante or caja_hostal)),
        'gastos': gastos,
        'modulo_fijo': modulo_fijo
    })

@login_required
def gestion_gastos(request):
    return _gestion_gastos_logica(request)

@login_required
def gestion_gastos_restaurante(request):
    return _gestion_gastos_logica(request, 'restaurante')

@login_required
def gestion_gastos_hostal(request):
    return _gestion_gastos_logica(request, 'hostal')

from pedidos.models import Factura, Pedido
from django.db.models import Sum
from django.contrib import messages

@login_required
def gestion_caja(request):
    # Buscar si hay alguna caja abierta (compartida entre todos)
    caja_abierta = SesionCaja.objects.filter(estado=True).first()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'abrir':
            if caja_abierta:
                messages.warning(request, "Ya existe una caja abierta.")
                return redirect('caja:gestion_caja')
                
            monto = request.POST.get('monto_inicial')
            SesionCaja.objects.create(
                usuario=request.user,
                monto_inicial=monto
            )
            messages.success(request, "Caja aperturada correctamente.")
            return redirect('caja:gestion_caja')
            
        elif action == 'cerrar':
            if caja_abierta:
                dinero_fisico = float(request.POST.get('monto_fisico'))
                
                # Calcular ventas del sistema DESDE que abrió la caja (Todas las ventas)
                ventas_sistema = Factura.objects.filter(
                    fecha_emision__gte=caja_abierta.fecha_apertura
                ).aggregate(Sum('total'))['total__sum'] or 0
                
                # Calcular gastos de esta sesión
                gastos_caja = caja_abierta.gastos.aggregate(Sum('monto'))['monto__sum'] or 0
                
                caja_abierta.monto_final_sistema = ventas_sistema
                caja_abierta.monto_final_fisico = dinero_fisico
                # Diferencia = Efectivo Real - (Efectivo Esperado: Inicial + Ventas - Gastos)
                efectivo_esperado = float(caja_abierta.monto_inicial) + float(ventas_sistema) - float(gastos_caja)
                caja_abierta.diferencia = float(dinero_fisico) - efectivo_esperado
                caja_abierta.fecha_cierre = timezone.now()
                caja_abierta.estado = False
                caja_abierta.save()
                
                messages.success(request, f"Caja cerrada. Diferencia: ${caja_abierta.diferencia}")
                return redirect('caja:gestion_caja')

    # Historial de cajas
    historial = []
    if request.user.rol in ['gerente', 'admin']:
        # Gerente ve TODAS las cajas (para auditar cierres de meseros)
        historial = SesionCaja.objects.annotate(
            total_gastos=Sum('gastos__monto')
        ).all().order_by('-fecha_apertura')[:20]
    elif request.user.rol == 'mesero':
        # Mesero no ve historial (según requerimiento anterior)
        historial = []
    else:
        # Default (otros roles si los hubiera): ven lo suyo
        historial = SesionCaja.objects.filter(usuario=request.user).annotate(
            total_gastos=Sum('gastos__monto')
        ).order_by('-fecha_apertura')[:10]
    
    # Calcular ventas y gastos actuales si la caja está abierta
    ventas_actuales = 0
    gastos_actuales = 0
    saldo_actual = 0
    if caja_abierta:
        # Gastos vinculados a esta sesión
        gastos_actuales = caja_abierta.gastos.aggregate(Sum('monto'))['monto__sum'] or 0

        # Ventas acumuladas globales del sistema
        ventas_actuales = Factura.objects.filter(
            fecha_emision__gte=caja_abierta.fecha_apertura
        ).aggregate(Sum('total'))['total__sum'] or 0
        saldo_actual = float(caja_abierta.monto_inicial) + float(ventas_actuales) - float(gastos_actuales)

    return render(request, 'caja/gestion_caja.html', {
        'caja_abierta': caja_abierta,
        'historial': historial,
        'ventas_actuales': ventas_actuales,
        'gastos_actuales': gastos_actuales,
        'saldo_actual': saldo_actual
    })

@login_required
def detalle_caja_modal(request, session_id):
    from pedidos.models import Factura
    sesion = get_object_or_404(SesionCaja, id=session_id)
    
    # Rango de tiempo de la sesión
    fecha_fin = sesion.fecha_cierre or timezone.now()
    ventas = Factura.objects.filter(
        fecha_emision__gte=sesion.fecha_apertura,
        fecha_emision__lte=fecha_fin
    ).select_related('pedido__mesero', 'cliente').order_by('-fecha_emision')
    
    # Gastos vinculados
    gastos = sesion.gastos.all().select_related('usuario').order_by('-fecha')
    total_gastos = gastos.aggregate(Sum('monto'))['monto__sum'] or 0
    
    return render(request, 'caja/modals/detalle_caja.html', {
        'sesion': sesion,
        'ventas': ventas,
        'gastos': gastos,
        'total_gastos': total_gastos
    })

@login_required
@gerente_required
def eliminar_caja(request, session_id):
    caja = get_object_or_404(SesionCaja, id=session_id)
    caja.delete()
    messages.success(request, "Registro de caja eliminado.")
    return redirect('caja:gestion_caja')

@login_required
@gerente_required
def editar_caja_modal(request, session_id):
    sesion = get_object_or_404(SesionCaja, id=session_id)
    if request.method == 'POST':
        sesion.monto_inicial = request.POST.get('monto_inicial')
        sesion.monto_final_sistema = request.POST.get('monto_final_sistema') or None
        sesion.monto_final_fisico = request.POST.get('monto_final_fisico') or None
        
        # Recalcular Diferencia if possible
        if sesion.monto_final_fisico and sesion.monto_final_sistema:
            from django.db.models import Sum
            gastos = sesion.gastos.aggregate(Sum('monto'))['monto__sum'] or 0
            esperado = float(sesion.monto_inicial) + float(sesion.monto_final_sistema) - float(gastos)
            sesion.diferencia = float(sesion.monto_final_fisico) - esperado
            
        sesion.save()
        messages.success(request, "Caja actualizada.")
        return redirect('caja:gestion_caja')

    return render(request, 'caja/modals/editar_caja.html', {'sesion': sesion})

from django.db.models.functions import TruncDate
@login_required
@gerente_required
def unificar_cajas(request):
    """Une todas las cajas del restaurante que fueron abiertas el mismo día en un solo registro."""
    if request.method == 'POST':
        # Agrupar por fecha
        fechas = SesionCaja.objects.annotate(dia=TruncDate('fecha_apertura')).values('dia').distinct()
        
        for f in fechas:
            cajas_dia = SesionCaja.objects.filter(fecha_apertura__date=f['dia']).order_by('fecha_apertura')
            if cajas_dia.count() > 1:
                principal = cajas_dia[0]
                otras = cajas_dia[1:]
                
                for c in otras:
                    principal.monto_inicial += c.monto_inicial
                    principal.monto_final_sistema = (principal.monto_final_sistema or 0) + (c.monto_final_sistema or 0)
                    principal.monto_final_fisico = (principal.monto_final_fisico or 0) + (c.monto_final_fisico or 0)
                    # Re-vincular gastos
                    c.gastos.update(sesion_caja=principal)
                    c.delete()
                
                # Recalcular diferencia de la principal
                gastos_tot = principal.gastos.aggregate(Sum('monto'))['monto__sum'] or 0
                if principal.monto_final_fisico is not None:
                    esperado = float(principal.monto_inicial) + float(principal.monto_final_sistema or 0) - float(gastos_tot)
                    principal.diferencia = float(principal.monto_final_fisico) - esperado
                
                principal.save()
        
        messages.success(request, "Se han unificado todas las cajas por día correctamente.")
    return redirect('caja:gestion_caja')
