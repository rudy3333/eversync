from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm
# Create your views here.
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.contrib.auth.views import PasswordChangeView
from .forms import UsernameChangeForm, DocumentForm, EventForm, NoteForm
from .models import Document, Event, Notes, Embed
from django.contrib import messages
from allauth.account.views import LoginView as AllauthLoginView
import os
from pathlib import Path
import micawber
import requests
from django.views.decorators.clickjacking import xframe_options_exempt
from webpush import send_user_notification
from icalendar import Calendar, Event as IcalEvent
from django.utils.text import slugify

providers = micawber.bootstrap_basic()

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
    payload = {"head": "Welcome!", "body": "Hello World"}

    send_user_notification(user=user, payload=payload, ttl=1000)


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
def calendar_event_delete(request, event_id):
    if request.method == 'POST':
        try:
            event = Event.objects.get(id=event_id)
            try:
                event.delete()
                return JsonResponse({'messsage': 'Success.'})
            except:
                return JsonResponse({'error': 'Error.'}, status=404)
        except:
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
            "id": event.id,
            "title": event.title,
            "start": event.start_time.isoformat(),
            "end": event.end_time.isoformat(),
            "color": event.color
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
    

@login_required
def note_add(request):
    if request.method == 'POST':
        form = NoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.user = request.user
            note.save()
            return JsonResponse({'message': 'Note created'}, status=201)
    else:
        return JsonResponse({'message': 'Error'}, status=400)
    
@login_required
def note_list(request):
    notes = Notes.objects.filter(user_id=request.user)
    notes_data = [
        {
        "id": note.id,
        "content": note.content.replace('\n', '<br>'),
        "title": note.title,
        "time": note.created_at
        }
        for note in notes
    ]
    return JsonResponse(notes_data, safe=False)

@login_required
def notes(request):
    notes = Notes.objects.filter(user_id=request.user)
    notes_data = [
        {
        "content": note.content.replace('\n', '<br>'),
        "title": note.title,
        }
        for note in notes
    ]
    return render(request, 'notes.html', {'notes_data': notes_data})


@login_required
def download_calendar(request, event_id):
    eventz = Event.objects.get(id=event_id, user=request.user)
    
    cal = Calendar()
    event = IcalEvent()
    event.add('summary', eventz.title)
    event.add('dtstart', eventz.start_time)
    event.add('dtend', eventz.end_time)
    event.add('uid', f'{eventz.id}@eversync') 

    cal.add_component(event)

    filename = f"{slugify(eventz.title)}.ics"
    response = HttpResponse(cal.to_ical(), content_type='text/calendar')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

    
@login_required
def pomodoro(request):
    return render(request, "pomodoro.html")

@login_required

def add_embed(request):
    if request.method == 'POST':
        url = request.POST["url"]
        if "x.com" in url:
            url = url.replace("x.com", "twitter.com")
        info = providers.request(url)

        embed = Embed.objects.create(
            url=url,
            title=info.get("title", "No title"),
            embed_html=info.get("html", "")
        )
        return redirect("embed_list")
    return render(request, "add_embed.html")

    
def embed_list(request):
    embeds = Embed.objects.all()
    return render(request, "embed_list.html", {"embeds": embeds})

@login_required
def delete_embed(request, id):
    if request.method == 'POST':
        try:
            embed = Embed.objects.get(id=id)
            try:
                embed.delete()
                return redirect('embed_list')
            except:
                return JsonResponse({'error': 'Error.'}, status=404)
        except:
            return JsonResponse({'error': 'Error.'}, status=404)
        
@login_required
def meeting(request):
    return render(request, 'meeting.html')

@login_required
def weather_api(request, location):
    # Step 1: Geocode the location
    url = f'https://nominatim.openstreetmap.org/search?q={location}&format=json'
    headers = {
        'User-Agent': 'my-weather-app'
    }
    geo_response = requests.get(url, headers=headers).json()

    if not geo_response:
        return JsonResponse({'error': 'Location not found'}, status=404)

    lat = geo_response[0]["lat"]
    lon = geo_response[0]["lon"]

    # Step 2: Call Open-Meteo's raw JSON API
    weather_url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,weathercode,precipitation_probability,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,sunrise,sunset,weathercode",
        "current_weather": True,
        "timezone": "auto"
    }

    weather_response = requests.get(weather_url, params=params).json()

    # Construct response
    hourly = weather_response["hourly"]
    daily = weather_response["daily"]
    current = weather_response["current_weather"]

    data = {
        "current": {
            "temperature": current["temperature"],
            "wind_speed": current["windspeed"],
            "weathercode": current["weathercode"]
        },
        "summary": {
            "today": {
                "max_temp": daily["temperature_2m_max"][0],
                "min_temp": daily["temperature_2m_min"][0],
                "sunrise": daily["sunrise"][0],
                "sunset": daily["sunset"][0],
                "weathercode": daily["weathercode"][0]
            }
        },
        "hourly": {
            "time": hourly["time"],
            "temperature_2m": hourly["temperature_2m"],
            "weathercode": hourly["weathercode"],
            "precipitation_probability": hourly["precipitation_probability"],
            "wind_speed_10m": hourly["wind_speed_10m"]
        },
        "daily": {
            "time": daily["time"],
            "temperature_max": daily["temperature_2m_max"],
            "temperature_min": daily["temperature_2m_min"],
            "sunrise": daily["sunrise"],
            "sunset": daily["sunset"],
            "weathercode": daily["weathercode"]
        }
    }
    return JsonResponse(data)

@login_required
@xframe_options_exempt
def weather_view(request, location):
    return render(request, "weather.html", {"location": location})

@login_required
def weather_pick(request):
    return render(request, "weather_pick.html")

@login_required
def note_delete(request, note_id):
    if request.method == 'POST':
        try:
            note = Notes.objects.get(id=note_id, user=request.user)
            note.delete()
            return JsonResponse({'message': 'Note deleted'}, status=200)
        except Notes.DoesNotExist:
            return JsonResponse({'error': 'Note not found'}, status=404)
    return JsonResponse({'error': 'Invalid request'}, status=400)