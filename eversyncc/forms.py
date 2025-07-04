from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import Document, Event, Notes, Task, WebArchive
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=False)
    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox)

    class Meta:
        model=User
        fields = ["username", "password1", "password2", "captcha"]

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
        fields = ['title', 'start_time', 'end_time', 'color', 'recurrence', 'recurrence_end']

class NoteForm(forms.ModelForm):
    class Meta:
        model = Notes
        fields = ['title', 'content']

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'completed']
        exclude = ['completed']


class EmailUpdateForm(forms.Form):
    email = forms.EmailField(label="Your email", required=True)

class WebArchiveForm(forms.ModelForm):
    class Meta:
        model = WebArchive
        fields = ['url']
        widgets = {
            'url': forms.URLInput(attrs={'placeholder': 'Enter URL to archive'})
        }

    def save(self, commit=True, user=None):
        instance = super().save(commit=False)
        if user:
            instance.user = user
        if commit:
            instance.save()
        return instance