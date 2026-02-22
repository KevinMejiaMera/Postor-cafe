from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from functools import wraps
from django.shortcuts import redirect

def role_required(allowed_roles=[]):
    """
    Decorador para restringir el acceso basado en el rol del usuario.
    :param allowed_roles: Lista de roles permitidos (ej. ['gerente', 'admin'])
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('usuarios:login')
            
            # Asumimos que request.user tiene un atributo 'rol'
            # y que 'admin' siempre tiene acceso (opcional, pero común)
            if request.user.rol in allowed_roles or request.user.rol == 'admin':
                return view_func(request, *args, **kwargs)
            
            # Si no tiene permiso, lanzar 403 o redirigir
            raise PermissionDenied
            
        return _wrapped_view
    return decorator

# --- Decoradores Específicos para el Proyecto ---

# Gerente (Admin ya incluido por lógica en role_required)
def gerente_required(view_func):
    return role_required(['gerente'])(view_func)

# Cocina
def cocina_required(view_func):
    return role_required(['cocina'])(view_func)

# Mesero
def mesero_required(view_func):
    return role_required(['mesero'])(view_func)

# Cajero (si existiera en el futuro, por ahora usamos gerente o lógica ad-hoc)
def cajero_required(view_func):
    return role_required(['cajero', 'gerente'])(view_func) # Ejemplo con cajero y gerente
