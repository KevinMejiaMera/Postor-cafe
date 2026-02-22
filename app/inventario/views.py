from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .models import Insumo, MovimientoKardex
from .forms import InsumoForm, MovimientoKardexForm
from core.decorators import gerente_required

@login_required
@gerente_required
def crear_insumo(request):
        
    if request.method == 'POST':
        form = InsumoForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
    else:
        form = InsumoForm()
    
    return render(request, 'pedidos/modals/form_producto.html', {'form': form, 'titulo': 'Nuevo Insumo'})

@login_required
@gerente_required
def editar_insumo(request, pk):

    insumo = get_object_or_404(Insumo, pk=pk)
    if request.method == 'POST':
        form = InsumoForm(request.POST, instance=insumo)
        if form.is_valid():
            form.save()
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
    else:
        form = InsumoForm(instance=insumo)
    
    return render(request, 'pedidos/modals/form_producto.html', {'form': form, 'titulo': f'Editar {insumo.nombre}'})

@login_required
@gerente_required
def registrar_movimiento(request):
        
    if request.method == 'POST':
        form = MovimientoKardexForm(request.POST)
        if form.is_valid():
            movimiento = form.save(commit=False)
            movimiento.usuario = request.user
            
            # Actualizar stock del insumo
            insumo = movimiento.insumo
            if movimiento.tipo == 'entrada':
                insumo.stock_actual += movimiento.cantidad
                # Recalcular costo promedio (simple)
                if insumo.stock_actual > 0:
                     valor_actual = (insumo.stock_actual - movimiento.cantidad) * insumo.costo_unitario
                     nuevo_valor_total = valor_actual + movimiento.costo_total
                     insumo.costo_unitario = nuevo_valor_total / insumo.stock_actual
            elif movimiento.tipo == 'salida':
                insumo.stock_actual -= movimiento.cantidad
            
            insumo.save()
            movimiento.save()
            
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
    else:
        form = MovimientoKardexForm(initial={'tipo': 'entrada'})
    
    return render(request, 'pedidos/modals/form_producto.html', {'form': form, 'titulo': 'Registrar Movimiento'})

@login_required
@gerente_required
def eliminar_insumo(request, pk):
        
    insumo = get_object_or_404(Insumo, pk=pk)
    
    if request.method == 'POST':
        insumo.delete()
        return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
        
    return HttpResponse(status=405)
