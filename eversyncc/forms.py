from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=False)

    class Meta:
        model=User
        fields = ["username", "password1", "password2"]