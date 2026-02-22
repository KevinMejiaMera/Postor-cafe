
@login_required
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
