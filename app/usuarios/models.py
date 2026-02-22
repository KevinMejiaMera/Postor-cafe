
# Create your models here.
# 📁 usuarios/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager

class UsuarioManager(BaseUserManager):
    
    def create_user(self, username, email, password=None, **extra_fields):
        """
        Crea y guarda un Usuario regular con el email y contraseña dados.
        """
        if not email:
            raise ValueError('El email es obligatorio')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        """
        Crea y guarda un Superusuario con el email y contraseña dados.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        # 👇 ¡ESTA LÍNEA ES LA MAGIA! 👇
        extra_fields.setdefault('rol', 'admin') # Asigna el rol 'admin'

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser debe tener is_superuser=True.')
        if extra_fields.get('rol') != 'admin':
            raise ValueError('Superuser debe tener rol="admin".')

        return self.create_user(username, email, password, **extra_fields)
# --- FIN DEL MANAGER ---


# --- Tu modelo Usuario ---
class Usuario(AbstractUser):
    ROL_CHOICES = [
        ('admin', 'Administrador'),
        ('mesero', 'Mesero'),
        ('cocina', 'Cocinero'),
        ('gerente', 'Gerente'),
    ]
    email = models.EmailField(unique=True)
    rol = models.CharField(max_length=10, choices=ROL_CHOICES, default='mesero')
    REQUIRED_FIELDS = ['email', 'cedula']
    cedula = models.CharField(max_length=10, unique=True, null=True, blank=True)
    telefono = models.CharField(max_length=15, null=True, blank=True)
    cedula = models.CharField(max_length=10, unique=True, null=True, blank=True)
    telefono = models.CharField(max_length=15, null=True, blank=True)
    direccion = models.TextField(null=True, blank=True)
    last_activity = models.DateTimeField(null=True, blank=True) # Para control de Online/Offline

    objects = UsuarioManager()

    def __str__(self):
        return self.username


# --- Tu modelo AuditLog ---
class AuditLog(models.Model):
    user = models.ForeignKey('Usuario', on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    action = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        user_display = self.user.username if self.user else "Anonymous"
        return f'{user_display} - {self.action} at {self.timestamp.strftime("%Y-%m-%d %H:%M")}'  # Se pide al crear superusuario
    
    