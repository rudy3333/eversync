from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import Document, Event

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=False)

    class Meta:
        model=User
        fields = ["username", "password1", "password2"]

class UsernameChangeForm(forms.Form):
    new_username = forms.CharField(max_length=150, required=True)

    def clean_new_username(self):
        new_username = self.cleaned_data.get('new_username')
        if User.objects.filter(username=new_username).exists():
            raise forms.ValidationError("This username is already taken.")
        return new_username
    
class ChangePasswordForm(forms.Form):
    old_password = forms.CharField(widget=forms.PasswordInput())
    new_password = forms.CharField(widget=forms.PasswordInput())

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['file']

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.title = self.cleaned_data['file'].name
        if commit:
            instance.save()
        return instance
    
class EventForm(forms.ModelForm):
    class Meta:
        model = Event 
        fields = ['title', 'start_time', 'end_time']