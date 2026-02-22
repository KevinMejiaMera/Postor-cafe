from django import forms
from .models import Usuario

class CrearUsuarioForm(forms.ModelForm):
    # Definimos explícitamente los campos de contraseña para asegurar que se rendericen
    password_1 = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'})
    )
    password_2 = forms.CharField(
        label='Confirmar Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Repita la contraseña'})
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(CrearUsuarioForm, self).__init__(*args, **kwargs)
        
        # Filtramos las opciones de rol si el usuario no es admin/superuser
        if self.user and self.user.rol != 'admin' and not self.user.is_superuser:
            # Excluimos 'admin' de las opciones
            current_choices = self.fields['rol'].choices
            self.fields['rol'].choices = [choice for choice in current_choices if choice[0] != 'admin']

    class Meta:
        model = Usuario
        fields = ('username', 'email', 'rol', 'cedula', 'telefono', 'direccion', 'first_name', 'last_name')
        widgets = {
            'rol': forms.Select(attrs={'class': 'form-select'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'cedula': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password_1")
        p2 = cleaned_data.get("password_2")
        if p1 and p2 and p1 != p2:
            self.add_error('password_2', "Las contraseñas no coinciden")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password_1"])
        if commit:
            user.save()
        return user

class EditarUsuarioForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(EditarUsuarioForm, self).__init__(*args, **kwargs)
        
        # Filtramos las opciones de rol si el usuario no es admin/superuser
        if self.user and self.user.rol != 'admin' and not self.user.is_superuser:
            current_choices = self.fields['rol'].choices
            self.fields['rol'].choices = [choice for choice in current_choices if choice[0] != 'admin']

    class Meta:
        model = Usuario
        fields = ('username', 'email', 'rol', 'cedula', 'telefono', 'direccion', 'first_name', 'last_name')
        widgets = {
            'rol': forms.Select(attrs={'class': 'form-select'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'cedula': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }
