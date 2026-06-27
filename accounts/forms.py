from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import User

class RegisterForm(forms.ModelForm):
    password  = forms.CharField(widget=forms.PasswordInput, min_length=8)
    password2 = forms.CharField(widget=forms.PasswordInput, label='Confirm Password')
    reg_code  = forms.CharField(required=False, label='Registration Code')
    terms     = forms.BooleanField(
        required=True,
        label='Terms Agreement',
        error_messages={'required': 'You must agree to the Terms of Service and Privacy Policy to register.'},
    )

    class Meta:
        model  = User
        fields = ['first_name','last_name','email','phone','country','state','dial_code','password','password2','reg_code','terms']

    def clean(self):
        data = super().clean()
        if data.get('password') != data.get('password2'):
            raise forms.ValidationError('Passwords do not match.')
        return data

class LoginForm(AuthenticationForm):
    username = forms.EmailField(label='Email Address')

class ProfileForm(forms.ModelForm):
    class Meta:
        model  = User
        fields = ['first_name','last_name','phone','country','state','dial_code','address','date_of_birth','gender','avatar']
        widgets = {'date_of_birth': forms.DateInput(attrs={'type':'date'})}

class ChangePasswordForm(forms.Form):
    current_password = forms.CharField(widget=forms.PasswordInput)
    new_password     = forms.CharField(widget=forms.PasswordInput, min_length=8)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        data = super().clean()
        if data.get('new_password') != data.get('confirm_password'):
            raise forms.ValidationError('Passwords do not match.')
        return data

class WithdrawalPINForm(forms.Form):
    current_pin = forms.CharField(max_length=4, required=False, widget=forms.PasswordInput)
    new_pin     = forms.CharField(max_length=4, min_length=4)
    confirm_pin = forms.CharField(max_length=4, min_length=4)

    def clean(self):
        data = super().clean()
        if data.get('new_pin') != data.get('confirm_pin'):
            raise forms.ValidationError('PINs do not match.')
        if data.get('new_pin') and not data['new_pin'].isdigit():
            raise forms.ValidationError('PIN must be 4 digits.')
        return data
