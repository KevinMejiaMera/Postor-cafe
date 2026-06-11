#!/bin/bash
# Ejecutar dentro del contenedor Docker cuando esté corriendo
# docker compose exec web bash -c "cd /app && bash printer/setup_impresion.sh"

echo "=== Setup del Módulo de Impresión Postor Cafe ==="
echo ""

# 1. Migraciones
echo ">>> Ejecutando migraciones de printer..."
python manage.py makemigrations printer
python manage.py migrate printer
echo ""

# 2. Generar token para agente Windows
echo ">>> Generando token para agente de impresión..."
python manage.py generate_printer_token agente_impresion --reset
echo ""

# 3. Crear impresoras por defecto (opcional)
echo ">>> Creando impresoras por defecto..."
python manage.py shell << 'EOF'
from printer.models import Printer

# Impresora cocina
if not Printer.objects.filter(name__icontains='Cocina').exists():
    p = Printer.objects.create(
        name='Impresora Cocina (Comandas)',
        printer_type='rawbt',
        rawbt_host='192.168.1.100',
        rawbt_port=8081,
        is_active=True
    )
    p.config = {'prints_command': True}
    p.save()
    print("✅ Impresora de Cocina creada")

# Impresora factura
if not Printer.objects.filter(name__icontains='Factura').exists():
    p = Printer.objects.create(
        name='Impresora Factura (Tickets)',
        printer_type='rawbt',
        rawbt_host='192.168.1.101',
        rawbt_port=8081,
        is_active=True
    )
    p.config = {'prints_receipt': True}
    p.save()
    print("✅ Impresora de Factura creada")
EOF
echo ""

echo "=== Setup completado ==="
echo "⚠️  Actualiza las IPs de las impresoras desde el panel Gerente > Impresoras"
EOF
