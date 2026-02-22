from django.db import models
from django.utils import timezone
from clientes.models import Cliente

class TipoHabitacion(models.Model):
    nombre = models.CharField(max_length=50)  # Ej: Simple, Doble, Matrimonial
    descripcion = models.TextField(blank=True, null=True)
    precio_noche = models.DecimalField(max_digits=10, decimal_places=2)
    capacidad_personas = models.PositiveIntegerField(default=1)
    
    def __str__(self):
        return f"{self.nombre} - ${self.precio_noche}"

class Habitacion(models.Model):
    ESTADOS = [
        ('disponible', 'Disponible'),
        ('ocupada', 'Ocupada'),
        ('limpieza', 'Limpieza / Mantenimiento'),
        ('reservada', 'Reservada'),
    ]
    
    numero = models.CharField(max_length=10, unique=True)  # Ej: "101", "204B"
    tipo = models.ForeignKey(TipoHabitacion, on_delete=models.SET_NULL, null=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='disponible')
    piso = models.CharField(max_length=10, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    # Precio personalizado (Sobrescribe el del tipo)
    precio_personalizado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Campo para control rápido de limpieza
    esta_limpia = models.BooleanField(default=True)

    def __str__(self):
        return f"Habitación {self.numero} ({self.tipo.nombre if self.tipo else 'Sin Tipo'})"
    
    @property
    def precio_actual(self):
        """Devuelve el precio personalizado si existe, o el del tipo."""
        if self.precio_personalizado:
            return self.precio_personalizado
        return self.tipo.precio_noche if self.tipo else 0
        
    @property
    def reserva_actual(self):
        return self.reservas.filter(estado='checkin').order_by('-id').first()

    @property
    def proxima_reserva(self):
        from django.utils import timezone
        return self.reservas.filter(
            estado='pendiente', 
            fecha_checkin__date__gte=timezone.localdate()
        ).order_by('fecha_checkin').first()

class Huesped(models.Model):
    # Puede ser un cliente del restaurante o un huesped exclusivo
    nombre_completo = models.CharField(max_length=100)
    documento_identidad = models.CharField(max_length=20, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    ciudad_origen = models.CharField(max_length=100, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre_completo

class Reserva(models.Model):
    ESTADOS_RESERVA = [
        ('pendiente', 'Pendiente / Confirmada'),
        ('checkin', 'Check-In (Hospedado)'),
        ('checkout', 'Check-Out (Finalizado)'),
        ('cancelada', 'Cancelada'),
    ]

    huesped = models.ForeignKey(Huesped, on_delete=models.CASCADE, related_name='reservas')
    habitacion = models.ForeignKey(Habitacion, on_delete=models.CASCADE, related_name='reservas')
    fecha_checkin = models.DateTimeField()
    fecha_checkout = models.DateTimeField()
    cantidad_personas = models.PositiveIntegerField(default=1)
    
    estado = models.CharField(max_length=20, choices=ESTADOS_RESERVA, default='pendiente')
    
    # Finanzas
    precio_total = models.DecimalField(max_digits=10, decimal_places=2, help_text="Costo total del alojamiento")
    pagado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    observaciones = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reserva {self.id} - {self.huesped} - Hab {self.habitacion.numero}"

    @property
    def noches(self):
        delta = self.fecha_checkout - self.fecha_checkin
        return max(1, delta.days)
