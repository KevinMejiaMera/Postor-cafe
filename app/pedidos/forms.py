from django import forms
from .models import Producto, CategoriaProducto

class CategoriaProductoForm(forms.ModelForm):
    class Meta:
        model = CategoriaProducto
        fields = ['nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-input', 'style': 'width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;'}),
        }

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'categoria', 'precio', 'stock', 'imagen', 'disponible']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-input', 'style': 'width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;'}),
            'categoria': forms.Select(attrs={'class': 'form-input', 'style': 'width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;'}),
            'precio': forms.NumberInput(attrs={'class': 'form-input', 'style': 'width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;'}),
            'stock': forms.NumberInput(attrs={'class': 'form-input', 'style': 'width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;'}),
            'imagen': forms.FileInput(attrs={'id': 'id_imagen', 'accept': 'image/*', 'style': 'display: none;'}),
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

from .models import Mesa

class MesaForm(forms.ModelForm):
    class Meta:
        model = Mesa
        fields = ['numero', 'capacidad']
        widgets = {
            'numero': forms.NumberInput(attrs={'class': 'form-input', 'style': 'width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;'}),
            'capacidad': forms.NumberInput(attrs={'class': 'form-input', 'style': 'width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;'}),
        }
