from django import forms
from .models import Insumo, MovimientoKardex

class InsumoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limpiar decimales redundantes para la vista (ej: 5.000 -> 5)
        if self.instance and self.instance.pk:
            for field in ['stock_actual', 'costo_unitario', 'stock_minimo']:
                val = getattr(self.instance, field)
                if val is not None:
                    # Normalizamos el valor para eliminar ceros a la derecha
                    self.initial[field] = val.normalize()

    class Meta:
        model = Insumo
        fields = ['nombre', 'unidad_medida', 'stock_actual', 'costo_unitario', 'stock_minimo', 'es_subreceta', 'rendimiento_receta']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-input', 'style': 'width: 100%; padding: 8px;'}),
            'unidad_medida': forms.Select(attrs={'class': 'form-select', 'style': 'width: 100%; padding: 8px;'}),
            'stock_actual': forms.NumberInput(attrs={'class': 'form-input', 'style': 'width: 100%; padding: 8px;', 'step': 'any'}),
            'costo_unitario': forms.NumberInput(attrs={'class': 'form-input', 'style': 'width: 100%; padding: 8px;', 'step': 'any'}),
            'stock_minimo': forms.NumberInput(attrs={'class': 'form-input', 'style': 'width: 100%; padding: 8px;', 'step': 'any'}),
            'es_subreceta': forms.CheckboxInput(attrs={'style': 'transform: scale(1.5); margin: 10px;'}),
            'rendimiento_receta': forms.NumberInput(attrs={'class': 'form-input', 'style': 'width: 100%; padding: 8px;', 'step': 'any'}),
        }

class MovimientoKardexForm(forms.ModelForm):
    class Meta:
        model = MovimientoKardex
        fields = ['insumo', 'tipo', 'cantidad', 'costo_total', 'observacion']
        widgets = {
            'insumo': forms.Select(attrs={'class': 'form-select', 'style': 'width: 100%; padding: 8px;'}),
            'tipo': forms.Select(attrs={'class': 'form-select', 'style': 'width: 100%; padding: 8px;'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-input', 'style': 'width: 100%; padding: 8px;', 'step': 'any'}),
            'costo_total': forms.NumberInput(attrs={'class': 'form-input', 'style': 'width: 100%; padding: 8px;', 'step': 'any'}),
            'observacion': forms.Textarea(attrs={'class': 'form-input', 'style': 'width: 100%; padding: 8px; height: 80px;'}),
        }
