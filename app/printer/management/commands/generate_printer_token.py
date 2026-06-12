from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

User = get_user_model()

class Command(BaseCommand):
    help = 'Genera token de autenticación para el agente de impresión'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Usuario para el agente')
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Regenerar token si ya existe'
        )

    def handle(self, *args, **options):
        username = options['username']
        reset = options['reset']
        
        # Crear o obtener usuario
        user, user_created = User.objects.get_or_create(
            username=username,
            defaults={
                'is_staff': True,      # Puede acceder al admin
                'is_superuser': True,  # Modo SISTEMA (ve todos los trabajos)
                'email': f'{username}@agente.local'
            }
        )
        
        if user_created:
            # Establecer contraseña solo si es nuevo
            password = User.objects.make_random_password(length=16)
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f'✅ Usuario "{username}" creado'))
            self.stdout.write(self.style.WARNING(f'   Contraseña: {password}'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠️ Usuario "{username}" ya existía'))
        
        # Generar o regenerar token
        if reset:
            Token.objects.filter(user=user).delete()
            token = Token.objects.create(user=user)
            self.stdout.write(self.style.SUCCESS(f'✅ Token regenerado'))
        else:
            token, token_created = Token.objects.get_or_create(user=user)
            if token_created:
                self.stdout.write(self.style.SUCCESS(f'✅ Token generado'))
            else:
                self.stdout.write(self.style.WARNING(f'⚠️ Token ya existía (usa --reset para regenerar)'))
        
        # Mostrar token
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('='*80))
        self.stdout.write(self.style.SUCCESS('TOKEN PARA AGENTE DE IMPRESIÓN'))
        self.stdout.write(self.style.SUCCESS('='*80))
        self.stdout.write(self.style.SUCCESS(f'Usuario: {username}'))
        self.stdout.write(self.style.SUCCESS(f'Token:   {token.key}'))
        self.stdout.write(self.style.SUCCESS('='*80))
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('⚠️ CONFIGURACIÓN DEL AGENTE WINDOWS:'))
        self.stdout.write(self.style.WARNING(f'   URL del Servidor: http://TU_IP:8002'))
        self.stdout.write(self.style.WARNING(f'   Token API:        {token.key}'))
        self.stdout.write('')
