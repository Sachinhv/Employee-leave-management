from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User


class RegisterForm(UserCreationForm):
    email      = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name  = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    department = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. IT, HR, Finance'}))
    phone      = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    employee_id= forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. EMP001'}))

    class Meta:
        model  = User
        fields = ['username', 'first_name', 'last_name', 'email',
                  'employee_id', 'department', 'phone',
                  'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not field.widget.attrs.get('class'):
                field.widget.attrs['class'] = 'form-control'

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean_employee_id(self):
        eid = self.cleaned_data.get('employee_id')
        if eid and User.objects.filter(employee_id=eid).exists():
            raise forms.ValidationError("This Employee ID already exists.")
        return eid


class ProfileForm(UserChangeForm):
    password = None

    class Meta:
        model  = User
        fields = ['first_name', 'last_name', 'email', 'department', 'phone']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
