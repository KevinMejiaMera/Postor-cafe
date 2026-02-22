

from django.db import models
from django.conf import settings
from clientes.models import Cliente


# 1. MESA
class Mesa(models.Model):
    numero = models.IntegerField(unique=True, verbose_name="Número de Mesa")
    capacidad = models.IntegerField(default=4)
    ESTADO_CHOICES = [
        ('libre', 'Libre'),
        ('ocupada', 'Ocupada'),
    ]
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='libre')

    def __str__(self):
        return f"Mesa {self.numero}"

# 2. PRODUCTO (Menú)
class Producto(models.Model):
    CATEGORIA_CHOICES = [
        ('entrada', 'Entrada'),
        ('plato_fuerte', 'Plato Fuerte'),
        ('bebida', 'Bebida'),
        ('postre', 'Postre'),
        ('otro', 'Otro'),
    ]

    nombre = models.CharField(max_length=100)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='otro', verbose_name="Categoría")
    stock = models.IntegerField(default=0, verbose_name="Stock Disponible")
    disponible = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} - ${self.precio}"

    # 👇 ESTA ES LA FUNCIÓN QUE FALTABA PARA EL COSTEO
    @property
    def costo_elaboracion(self):
        """Suma el costo de todos los ingredientes de la receta"""
        total = 0
        # 'receta' es el related_name definido en inventario/models.py
        for ingrediente in self.receta.all():
            if ingrediente.insumo:
                total += ingrediente.cantidad_necesaria * ingrediente.insumo.costo_unitario
        return total

# 3. PEDIDO (La cuenta)
class Pedido(models.Model):
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),       # Mesero tomando orden
        ('confirmado', 'En Cocina'),    # Enviado a cocina
        ('listo', 'Listo para Servir'), # Cocina terminó
        ('entregado', 'Entregado'),     # Comiendo
        ('pagado', 'Pagado'),           # Finalizado
        ('cancelado', 'Cancelado'),
    ]

    mesa = models.ForeignKey(Mesa, on_delete=models.SET_NULL, null=True, blank=True, related_name='pedidos')
    mesero = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.SET_NULL, null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='borrador')
    observacion = models.TextField(blank=True, null=True, verbose_name="Notas para Cocina")
    
    # Tiempos de Cocina
    fecha_confirmado = models.DateTimeField(null=True, blank=True, verbose_name="Hora enviado a Cocina")
    fecha_listo = models.DateTimeField(null=True, blank=True, verbose_name="Hora terminado en Cocina")
    # Nuevo campo para Agenda
    fecha_entrega = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Entrega/Reserva")
    
    # Notificaciones
    notificacion_vista = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Pedido #{self.id} - Mesa {self.mesa.numero}"
    
    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())

# 4. DETALLE (Platos del pedido)
class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2) # Guardamos precio histórico

    def save(self, *args, **kwargs):
        if not self.id:
            self.precio_unitario = self.producto.precio
        super().save(*args, **kwargs)

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario

# 5. FACTURA (Documento legal)
class Factura(models.Model):
    METODO_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta de Crédito/Débito'),
        ('transferencia', 'Transferencia Bancaria'),
    ]

    # Relación 1 a 1: Un pedido tiene una sola factura
    pedido = models.OneToOneField(Pedido, on_delete=models.CASCADE, related_name='factura')
    
    # Relación con Cliente (Opcional, si es Consumidor Final)
    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.PROTECT, null=True, blank=True)
    
    # --- DATOS HISTÓRICOS (Snapshot) ---
    # Guardamos estos datos aquí por si el cliente cambia sus datos en el futuro,
    # la factura histórica no se altere.
    razon_social = models.CharField(max_length=200, verbose_name="Nombre/Razón Social")
    ruc_ci = models.CharField(max_length=13, verbose_name="RUC/CI")
    direccion = models.CharField(max_length=200, blank=True, null=True)
    correo = models.EmailField(blank=True, null=True)
    
    # --- MONTOS ---
    fecha_emision = models.DateTimeField(auto_now_add=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    iva = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES, default='efectivo')

    def __str__(self):
        return f"Factura #{self.id} - {self.razon_social}"

    def save(self, *args, **kwargs):
        # Al guardar la factura, automáticamente marcamos el pedido como PAGADO
        if not self.id: # Solo al crear
            self.pedido.estado = 'pagado'
            self.pedido.save()
            
            # También liberamos la mesa automáticamente
            self.pedido.mesa.estado = 'libre'
            self.pedido.mesa.save()
            
        super().save(*args, **kwargs)