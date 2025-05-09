from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm
# Create your views here.
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.contrib.auth.views import PasswordChangeView
from .forms import UsernameChangeForm, DocumentForm, EventForm
from .models import Document, Event
from django.contrib import messages
from allauth.account.views import LoginView as AllauthLoginView
import os
from pathlib import Path



def logout_view(request):
    request.session.flush()
    logout(request)
    return redirect('login')

def register(request):
        if request.user.is_authenticated:
            return redirect('/')
        
        if request.method == "POST":
            form = UserCreationForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect("/")
        else:
            form = UserCreationForm()
        return render(request, "register.html", {"form": form})

@login_required
def index(request):
    return render(request, "index.html")

@login_required
def manage(request):
    form = PasswordChangeForm(user=request.user)
    return render(request, "manage.html", {"password_form": form})

@login_required
def change_username(request):
    if request.method == 'POST':
        form = UsernameChangeForm(request.POST)
        if form.is_valid():
            new_username = form.cleaned_data['new_username']
            user = request.user
            user.username = new_username
            user.save()
            messages.success(request, "Username updated successfully!")
            return redirect('manage')  # Redirect back to the manage account page
        else:
            messages.error(request, "Error: Username couldn't be updated.")
    else:
        form = UsernameChangeForm()

    return render(request, 'manage.html', {'form': form})


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Password updated successfully!")
            return redirect('manage')  # Redirect to an appropriate page
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PasswordChangeForm(user=request.user)
    return render(request, 'manage.html', {'password_form': form})

class RedirectFromLogin(AllauthLoginView):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('/') 
        return super().dispatch(request, *args, **kwargs)
    
@login_required
def upload_file(request):
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            filename = document.file.name
            ext = os.path.splitext(filename)[1].lower()

            forbidden_extensions=['.html','.htm','.php','.exe','.js','.sh','.bat']
            if ext in forbidden_extensions:
                request.session.flush()
                logout(request)
                return HttpResponse("<html><body><script>alert('Uploading possibly malicious files is forbidden. You have been logged out.'); location.reload();</script></body></html>")
            document.user = request.user
            document.save()
            return redirect('file_list')
    else:
        form = DocumentForm()
    return render(request, 'upload.html', {'form': form})

@login_required
def file_list(request):
    documents = Document.objects.filter(user=request.user)
    return render(request, 'file_list.html', {'documents': documents})


@login_required
def delete_file(request, file_id):
    if request.method == 'DELETE':
        try:
            file = Document.objects.get(id=file_id)
            file_path = file.file.path
            try:
                file.delete()
            except:
                pass
            os.remove(file_path)
            return JsonResponse({'message' : 'Success.'})
        except Document.DoesNotExist:
            return JsonResponse({'error': 'Error.'}, status=404)

@login_required
def calendar(request):
    events = Event.objects.filter(user=request.user)
    events_data = [
        {
            "title": event.title,
            "start": event.start_time.isoformat(),
            "end": event.end_time.isoformat(),
        }
        for event in events
    ]
    return render(request, 'calendar.html', {'events_data': events_data})

@login_required
def calendar_events(request):
    events = Event.objects.filter(user=request.user)
    events_data = [
        {
            "title": event.title,
            "start": event.start_time.isoformat(),
            "end": event.end_time.isoformat(),
        }
        for event in events
    ]
    return JsonResponse(events_data, safe=False)

@login_required
def calendar_event_create(request):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.user = request.user
            event.save()
            return JsonResponse({'message': 'Event created'}, status=201)
    else:
        return JsonResponse({'message': 'Error'}, status=400)