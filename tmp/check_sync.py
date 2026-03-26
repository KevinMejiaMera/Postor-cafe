import os
import django
import sys
import datetime
from django.utils import timezone
from django.db.models import Sum, F

# Add 'app' and the root to sys.path
sys.path.append(os.path.join(os.getcwd(), 'app'))
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'restaurante.settings')
django.setup()

from pedidos.models import Pedido, DetallePedido, Factura

def check_sync():
    hoy = timezone.localdate()
    print(f"--- CHECK SYNC ({hoy}) ---")
    
    # 1. Pedidos (excluding borrador)
    pedidos_count = Pedido.objects.exclude(estado='borrador').count()
    pedidos_pagados_count = Pedido.objects.filter(estado='pagado').count()
    print(f"Total Pedidos (not borrador): {pedidos_count}")
    print(f"Total Pedidos (pagado): {pedidos_pagados_count}")
    
    # 2. Facturas
    facturas_count = Factura.objects.all().count()
    facturas_hoy = Factura.objects.filter(fecha_emision__date=hoy)
    facturas_hoy_count = facturas_hoy.count()
    total_ventas_hoy = facturas_hoy.aggregate(Sum('total'))['total__sum'] or 0
    print(f"Total Facturas: {facturas_count}")
    print(f"Total Facturas (hoy): {facturas_hoy_count}")
    print(f"Total Ventas (hoy - Dashboard method): ${total_ventas_hoy}")
    
    # 3. DetallePedido
    detalles_pagados = DetallePedido.objects.filter(pedido__estado='pagado')
    total_detalles_hoy = detalles_pagados.filter(pedido__factura__fecha_emision__date=hoy).annotate(
        sub_total=F('cantidad') * F('precio_unitario')
    ).aggregate(Sum('sub_total'))['sub_total__sum'] or 0
    print(f"Total DetallePedido (pagado - Reports method): ${total_detalles_hoy}")
    
    # Check for orphaned Facturas
    facturas_without_pedidos = 0
    for f in Factura.objects.all():
        try:
            p = f.pedido
        except Pedido.DoesNotExist:
            facturas_without_pedidos += 1
    print(f"Facturas without Pedidos: {facturas_without_pedidos}")
    
    # Check for Pedidos that should have Factura but don't
    pedidos_pagados_without_factura = 0
    for p in Pedido.objects.filter(estado='pagado'):
        if not hasattr(p, 'factura'):
            pedidos_pagados_without_factura += 1
    print(f"Pedidos Pagados without Factura: {pedidos_pagados_without_factura}")

if __name__ == "__main__":
    check_sync()
