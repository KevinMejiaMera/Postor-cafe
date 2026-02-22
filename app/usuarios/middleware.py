from django.utils import timezone
from .models import Usuario

class UpdateLastActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        if request.user.is_authenticated:
            # Actualizamos last_activity sin disparar el save() completo para optimizar
            Usuario.objects.filter(pk=request.user.pk).update(last_activity=timezone.now())
            
        return response
