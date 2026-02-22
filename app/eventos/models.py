
from django.db import models
from pedidos.models import Producto

class CategoriaMenaje(models.Model):
    nombre = models.CharField(max_length=100)
    
    def __str__(self):
        return self.nombre

class Menaje(models.Model):
    nombre = models.CharField(max_length=150)
    categoria = models.ForeignKey(CategoriaMenaje, on_delete=models.CASCADE, related_name='items')
    costo_reposicion = models.DecimalField(max_digits=10, decimal_places=2, help_text="Costo si se rompe/pierde")
    costo_alquiler = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Costo de alquiler para el evento")
    
    def __str__(self):
        return f"{self.nombre} ({self.categoria.nombre})"

class Evento(models.Model):
    ESTADOS = [
        ('borrador', 'Borrador / Cotización'),
        ('confirmado', 'Confirmado'),
        ('finalizado', 'Finalizado'),
        ('cancelado', 'Cancelado'),
    ]
    
    TIPO_SERVICIO = [
        ('buffet', 'Buffet'),
        ('plato_servido', 'Plato Servido'),
        ('cocktail', 'Cocktail'),
        ('otro', 'Otro'),
    ]

    nombre = models.CharField(max_length=150, help_text="Ej: Boda Familia Pérez")
    fecha_evento = models.DateTimeField()
    hora_evento = models.TimeField(null=True, blank=True)
    personas = models.IntegerField(verbose_name="Cantidad de Personas (Pax)", default=10)
    tipo_servicio = models.CharField(max_length=50, choices=TIPO_SERVICIO, default='plato_servido')
    
    estado = models.CharField(max_length=20, choices=ESTADOS, default='borrador')
    
    # Campo legacy para compatibilidad, pero usaremos IngresoEvento principalmente
    presupuesto_por_persona = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Legacy: Precio venta por persona")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # --- Métodos de Costo ---
    def costo_comida(self):
        return sum(item.costo_total for item in self.menu_items.all())

    def costo_menaje(self):
        return sum(item.costo_total for item in self.items_menaje.all())
    
    def costo_gastos_extra(self):
        # Suma de gastos adicionales detallados
        return sum(gasto.total for gasto in self.gastos.all())

    def costo_total_evento(self):
        return self.costo_comida() + self.costo_menaje() + self.costo_gastos_extra()

    # --- Métodos de Ingreso ---
    def ingreso_total(self):
        ingresos_detallados = sum(ing.total for ing in self.ingresos.all())
        # Fallback si no hay ingresos detallados pero hay presupuesto_por_persona
        if ingresos_detallados == 0 and self.presupuesto_por_persona > 0:
            return self.presupuesto_por_persona * self.personas
        return ingresos_detallados

    def ganancia(self):
        return self.ingreso_total() - self.costo_total_evento()

    def margen_ganancia(self):
        venta = self.ingreso_total()
        if venta > 0:
            return (self.ganancia() / venta) * 100
        return 0

    def __str__(self):
        return f"{self.nombre} ({self.fecha_evento.date()})"


class DetalleMenu(models.Model):
    evento = models.ForeignKey(Evento, related_name='menu_items', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.IntegerField(default=1) 
    costo_unitario_snapshot = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    @property
    def costo_total(self):
        return self.cantidad * self.costo_unitario_snapshot

    def save(self, *args, **kwargs):
        if not self.costo_unitario_snapshot and self.producto:
            self.costo_unitario_snapshot = self.producto.costo_elaboracion
        super().save(*args, **kwargs)

class ItemMenajeEvento(models.Model):
    evento = models.ForeignKey(Evento, related_name='items_menaje', on_delete=models.CASCADE)
    menaje = models.ForeignKey(Menaje, on_delete=models.CASCADE)
    cantidad = models.IntegerField(default=1)
    costo_unitario_snapshot = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    @property
    def costo_total(self):
        return self.cantidad * self.costo_unitario_snapshot
    
    def save(self, *args, **kwargs):
        if not self.costo_unitario_snapshot and self.menaje:
            self.costo_unitario_snapshot = self.menaje.costo_alquiler
        super().save(*args, **kwargs)

class GastoEvento(models.Model):
    CATEGORIAS = [
        ('alquiler', 'Alquiler Equipos/Local'),
        ('ayb', 'Alimentos y Bebidas (Extra)'),
        ('decoracion', 'Decoración'),
        ('personal', 'Personal'),
        ('transporte', 'Transporte'),
        ('otros', 'Otros'),
    ]
    evento = models.ForeignKey(Evento, related_name='gastos', on_delete=models.CASCADE)
    nombre = models.CharField(max_length=150)
    categoria = models.CharField(max_length=50, choices=CATEGORIAS, default='otros')
    cantidad = models.IntegerField(default=1)
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    
    @property
    def total(self):
        return self.cantidad * self.costo_unitario
    
    def __str__(self):
        return f"{self.nombre}: ${self.total}"

class IngresoEvento(models.Model):
    CATEGORIAS = [
        ('menu_adulto', 'Menú Adultos'),
        ('menu_nino', 'Menú Niños'),
        ('bebidas', 'Bebidas/Licores'),
        ('servicios', 'Servicios Adicionales'),
        ('otros', 'Otros'),
    ]
    evento = models.ForeignKey(Evento, related_name='ingresos', on_delete=models.CASCADE)
    nombre = models.CharField(max_length=150, help_text="Ej: Menú Adulto Premium")
    categoria = models.CharField(max_length=50, choices=CATEGORIAS, default='menu_adulto')
    cantidad = models.IntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    
    @property
    def total(self):
        return self.cantidad * self.precio_unitario
    
    def __str__(self):
        return f"{self.nombre}: ${self.total}"

# Modelo legacy mantenido para evitar errores en migraciones si existen datos, 
# pero idealmente se migraría a GastoEvento
class CostoAdicional(models.Model):
    evento = models.ForeignKey(Evento, related_name='costos_extra', on_delete=models.CASCADE)
    descripcion = models.CharField(max_length=100)
    costo = models.DecimalField(max_digits=10, decimal_places=2)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2, default=0)

