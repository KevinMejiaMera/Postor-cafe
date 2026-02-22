from django import forms
from .models import Evento, DetalleMenu, CostoAdicional, GastoEvento, IngresoEvento, ItemMenajeEvento
from pedidos.models import Producto

class EventoForm(forms.ModelForm):
    class Meta:
        model = Evento
        # Fields used for FULL updates (e.g. in Simulator)
        fields = ['nombre', 'fecha_evento', 'hora_evento', 'personas', 'tipo_servicio', 'estado', 'presupuesto_por_persona']
        widgets = {
            'fecha_evento': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'hora_evento': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        }

class EventoCreateForm(forms.ModelForm):
    class Meta:
        model = Evento
        # Limited fields for the simplified creation modal
        fields = ['nombre', 'fecha_evento', 'personas']
        widgets = {
             'nombre': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej: Boda Familia...'}),
             'fecha_evento': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
             'personas': forms.NumberInput(attrs={'class': 'form-input', 'value': 10}),
        }

class DetalleMenuForm(forms.ModelForm):
    class Meta:
        model = DetalleMenu
        fields = ['producto', 'cantidad', 'costo_unitario_snapshot']

class CostoAdicionalForm(forms.ModelForm):
    class Meta:
        model = CostoAdicional
        fields = ['descripcion', 'costo', 'precio_venta']

class GastoEventoForm(forms.ModelForm):
    class Meta:
        model = GastoEvento
        fields = ['nombre', 'categoria', 'cantidad', 'costo_unitario']

class IngresoEventoForm(forms.ModelForm):
    class Meta:
        model = IngresoEvento
        fields = ['nombre', 'categoria', 'cantidad', 'precio_unitario']

class ItemMenajeEventoForm(forms.ModelForm):
    class Meta:
        model = ItemMenajeEvento
        fields = ['menaje', 'cantidad']
