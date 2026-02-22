from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import SesionCaja
from pedidos.models import Factura, Pedido
from django.db.models import Sum
from django.contrib import messages

@login_required
def gestion_caja(request):
    # Buscar si el usuario tiene una caja abierta
    caja_abierta = SesionCaja.objects.filter(usuario=request.user, estado=True).first()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'abrir':
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
                
                # Calcular ventas del sistema DESDE que abrió la caja
                if request.user.rol in ['gerente', 'admin']:
                    # El gerente/admin cierra la caja "General", sumando TODAS las ventas
                    ventas_sistema = Factura.objects.filter(
                        fecha_emision__gte=caja_abierta.fecha_apertura
                    ).aggregate(Sum('total'))['total__sum'] or 0
                else:
                    # El mesero cierra SU caja (ventas que él gestionó)
                    ventas_sistema = Factura.objects.filter(
                        pedido__mesero=request.user, 
                        fecha_emision__gte=caja_abierta.fecha_apertura
                    ).aggregate(Sum('total'))['total__sum'] or 0
                
                caja_abierta.monto_final_sistema = ventas_sistema
                caja_abierta.monto_final_fisico = dinero_fisico
                caja_abierta.diferencia = float(dinero_fisico) - (float(caja_abierta.monto_inicial) + float(ventas_sistema))
                caja_abierta.fecha_cierre = timezone.now()
                caja_abierta.estado = False
                caja_abierta.save()
                
                messages.success(request, f"Caja cerrada. Diferencia: ${caja_abierta.diferencia}")
                return redirect('caja:gestion_caja')

    # Historial de cajas
    historial = []
    if request.user.rol in ['gerente', 'admin']:
        # Gerente ve TODAS las cajas (para auditar cierres de meseros)
        historial = SesionCaja.objects.all().order_by('-fecha_apertura')[:20]
    elif request.user.rol == 'mesero':
        # Mesero no ve historial (según requerimiento anterior)
        historial = []
    else:
        # Default (otros roles si los hubiera): ven lo suyo
        historial = SesionCaja.objects.filter(usuario=request.user).order_by('-fecha_apertura')[:10]
    
    # Calcular ventas actuales si la caja está abierta (para mostrar en pantalla)
    ventas_actuales = 0
    if caja_abierta:
        # Si es mesero, NO mostramos ventas acumuladas ni globales
        if request.user.rol == 'mesero':
            ventas_actuales = None # Ocultar
        elif request.user.rol in ['gerente', 'admin']:
            ventas_actuales = Factura.objects.filter(
                fecha_emision__gte=caja_abierta.fecha_apertura
            ).aggregate(Sum('total'))['total__sum'] or 0
        else:
             # Default fallback
            ventas_actuales = Factura.objects.filter(
                pedido__mesero=request.user, 
                fecha_emision__gte=caja_abierta.fecha_apertura
            ).aggregate(Sum('total'))['total__sum'] or 0

    return render(request, 'caja/gestion_caja.html', {
        'caja_abierta': caja_abierta,
        'historial': historial,
        'ventas_actuales': ventas_actuales # <--- Nueva variable de contexto
    })
