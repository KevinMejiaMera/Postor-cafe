# 📁 clientes/views.py

from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse # Para respuestas simples
from .models import Cliente

@login_required
def buscar_cliente(request):
    query = request.GET.get('q', '')
    
    # 👇 Print para ver en la consola negra si llega la petición
    print(f"--- BUSCANDO CLIENTE: '{query}' ---")

    if not query:
        clientes = []
    else:
        # Usamos 'cedula_o_ruc' y 'nombres' que son los campos reales de tu modelo
        clientes = Cliente.objects.filter(
            Q(nombres__icontains=query) | 
            Q(cedula_o_ruc__icontains=query)
        )[:5] # Limitamos a 5 para no llenar la pantalla

    # 👇 Print para ver cuántos encontró
    print(f"--- CLIENTES ENCONTRADOS: {len(clientes)} ---")

    context = {'clientes': clientes}
    return render(request, 'clientes/partials/resultados_busqueda.html', context)

@login_required
def crear_cliente_modal(request):
    if request.method == 'POST':
        nombres = request.POST.get('nombres')
        cedula_o_ruc = request.POST.get('cedula_o_ruc')
        direccion = request.POST.get('direccion')
        telefono = request.POST.get('telefono')
        email = request.POST.get('email')

        # Creamos el cliente
        try:
            nuevo_cliente = Cliente.objects.create(
                nombres=nombres,
                cedula_o_ruc=cedula_o_ruc,
                direccion=direccion,
                telefono=telefono,
                email=email
            )
            context = {'nuevo_cliente': nuevo_cliente}
            return render(request, 'clientes/partials/cliente_creado_exito.html', context)
        except Exception as e:
            # En caso de error (duplicado, etc), devolvemos el formulario con error
            return render(request, 'clientes/partials/form_crear_cliente.html', {'error': str(e)})

    return render(request, 'clientes/partials/form_crear_cliente.html')