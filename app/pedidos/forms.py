from django import forms
from .models import Producto

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        # Ahora incluimos 'categoria'
        fields = ['nombre', 'categoria', 'precio', 'stock', 'disponible']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-input', 'style': 'width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;'}),
            'categoria': forms.Select(attrs={'class': 'form-input', 'style': 'width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;'}),
            'precio': forms.NumberInput(attrs={'class': 'form-input', 'style': 'width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;'}),
            'stock': forms.NumberInput(attrs={'class': 'form-input', 'style': 'width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;'}),
            'disponible': forms.CheckboxInput(attrs={'style': 'transform: scale(1.2); margin-left: 5px;'}),
        }

from inventario.models import Receta
class RecetaForm(forms.ModelForm):
    class Meta:
        model = Receta
        fields = ['insumo', 'cantidad_necesaria']
        labels = {
            'insumo': 'Ingrediente (Insumo)',
            'cantidad_necesaria': 'Cantidad (Ej: 0.200 para kg/gl o 1 para unidad)',
        }
        widgets = {
            'insumo': forms.Select(attrs={'class': 'form-input', 'style': 'width: 100%; padding: 8px;'}),
            'cantidad_necesaria': forms.NumberInput(attrs={'class': 'form-input', 'style': 'width: 100%; padding: 8px;', 'step': 'any'}),
        }
