from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, FileResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm
from django.core.files import File
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from django.utils import timezone
# Create your views here.
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.contrib.auth.views import PasswordChangeView
from .forms import UsernameChangeForm, DocumentForm, EventForm, NoteForm, TaskForm
from .models import Document, Event, Notes, Embed, Task, RichDocument, Message, WebArchive, MessageReaction
from django.contrib import messages
from allauth.account.views import LoginView as AllauthLoginView
import os
from pathlib import Path
from eversyncc.models import UserNotifs
import requests
from allauth.account.models import EmailAddress
from django.views.decorators.clickjacking import xframe_options_exempt
from selenium.webdriver.support.ui import WebDriverWait
from webpush import send_user_notification
from icalendar import Calendar, Event as IcalEvent
from django.utils.text import slugify
import json
import tempfile
from yt_dlp import YoutubeDL
from django.db.models import Q
from django.utils.timezone import now
from .embed_utils import get_embed_info
from .models import Whiteboard, Stroke
from eversyncc.email import verify_token
from django.contrib.auth import get_user_model
from .forms import EmailUpdateForm, WebArchiveForm
from allauth.account.utils import send_email_confirmation
from functools import wraps
from .forms import RegisterForm
from django.core.files.storage import FileSystemStorage
import uuid
from django.conf import settings
from fcm import send_push_notification
from .models import UserNotifs
import aiohttp
import asyncio
from asgiref.sync import sync_to_async
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import selenium
import pyclamd
from datetime import datetime, timedelta
from django_ratelimit.decorators import ratelimit
import re
import magic
import bleach

# Constants
FORBIDDEN_EXTENSIONS = ['.html', '.htm', '.php', '.exe', '.js', '.sh', '.bat']
SELENIUM_CHROME_ARGS = [
    '--headless=new',
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--disable-gpu',
    '--lang=en-US',
]
SELENIUM_CHROME_PREFS = {
    'intl.accept_languages': 'en,en_US',
    'profile.default_content_setting_values.geolocation': 2,
}

MAX_FILE_SIZE = 20 * 1024 * 1024

def scan_file_with_clamav(file_path):
    try:
        cd = pyclamd.ClamdNetworkSocket(host='127.0.0.1', port=3310)

        # Try to ping the daemon first! 🐱
        if cd.ping():
            print("ClamAV is alive~ :3")
            result = cd.scan_file(file_path)
            return result or None  # clean = None, infected = dict!
        else:
            print("ClamAV didn't respond :c (bypassing scan)")
            return None  # Bypass if not responding
    except pyclamd.ConnectionError as e:
        print(f"ClamAV ConnectionError: {str(e)} (bypassing scan)")
        return None  # Bypass if connection error
    except Exception as e:
        print(f"ClamAV Unexpected error: {str(e)} (bypassing scan)")
        return None  # Bypass on any unexpected error

def email_verified_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            try:
                email_address = EmailAddress.objects.get(user=request.user, email=request.user.email)
                if not email_address.verified:
                    return redirect('account_email')  # or your custom "please verify" page
            except EmailAddress.DoesNotExist:
                return redirect('account_email')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def logout_view(request):
    request.session.flush()
    logout(request)
    return redirect('login')

def register(request):
        if request.user.is_authenticated:
            return redirect('/')
        
        if request.method == "POST":
            form = RegisterForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect("/")
        else:
            form = RegisterForm()
        return render(request, "register.html", {"form": form})

@login_required
def index(request):
    return render(request, "index.html")

@login_required
def manage(request):
    form = PasswordChangeForm(user=request.user)
    return render(request, "manage.html", {"password_form": form})

@login_required
def delete_account(request):
    if request.method == "POST":
        user = request.user
        user_files = Document.objects.filter(user=user)

        for doc in user_files:
            if doc.file:
                doc.file.delete(save=False)
        user_files.delete()
        
        Notes.objects.filter(user=user).delete()
        Event.objects.filter(user=user).delete()
        Embed.objects.filter(user=user).delete()
        Task.objects.filter(user=user).delete()
        RichDocument.objects.filter(owner=user).delete()
        Message.objects.filter(sender=user).delete()
        Message.objects.filter(receiver=user).delete()
        WebArchive.objects.filter(user=user).delete()
        MessageReaction.objects.filter(user=user).delete()
        whiteboards = Whiteboard.objects.filter(owner=user)
        for wb in whiteboards:
            Stroke.objects.filter(whiteboard=wb).delete()
            wb.delete()
        UserNotifs.objects.filter(user=user).delete()
        request.session.flush()
        logout(request)
        user.delete()
        return redirect('index')

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

@email_verified_required
@login_required
def upload_file(request):
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            filename = re.sub(r'[^A-Za-z0-9._-]', '_', document.file.name)
            ext = os.path.splitext(filename)[1].lower()
            file_size = document.file.size

            mime = magic.from_buffer(document.file.read(2048), mime=True)
            document.file.seek(0)
            allowed_mimes = ['application/pdf', 'image/png', 'image/jpeg', 'text/plain']
            if mime not in allowed_mimes:
                return HttpResponse(
                    "<html><body><script>alert('Upload blocked: File type not allowed.'); window.history.back();</script></body></html>"
                )

            if ext in FORBIDDEN_EXTENSIONS:
                request.session.flush()
                logout(request)
                return HttpResponse("<html><body><script>alert('Uploading possibly malicious files is forbidden. You have been logged out.'); location.reload();</script></body></html>")

            if file_size > MAX_FILE_SIZE:
                return HttpResponse(
                    "<html><body><script>alert('Upload blocked: File size exceeds 20 MB limit.'); window.history.back();</script></body></html>"
                )

            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                for chunk in document.file.chunks():
                    temp_file.write(chunk)
                temp_file.flush()
                temp_file_path = temp_file.name

            os.chmod(temp_file_path, 0o644)

            scan_result = scan_file_with_clamav(temp_file_path)

            os.remove(temp_file_path)
            if scan_result is not None:
                if isinstance(scan_result, dict):
                    if "error" in scan_result:
                        error_message = f"ClamAV error: {scan_result['error']}"
                    else:
                        # infection detected
                        file_name, (status, virus_name) = next(iter(scan_result.items()))
                        error_message = f"File is infected with: {virus_name}"
                else:
                    error_message = "File blocked for unknown reason."

                return HttpResponse(f"""
                <html><body><script>
                    alert('Upload blocked: {error_message}');
                    window.history.back();
                </script></body></html>
                """)

            user_storage = request.user.userstorage
            if user_storage.used_storage + file_size > user_storage.storage_limit:
                return HttpResponse(
                    "<html><body><script>alert('Upload blocked: Storage limit exceeded. Please delete files.'); window.history.back();</script></body></html>"
                )

            document.user = request.user
            document.file.name = filename  # Use sanitized filename
            document.save()
            user_storage.used_storage += document.size
            user_storage.save()

            return redirect('file_list')
    else:
        form = DocumentForm()
    return render(request, 'upload.html', {'form': form})

@login_required
def file_list(request):
    documents = Document.objects.filter(user=request.user)
    user_storage = request.user.userstorage

    used_mb = user_storage.used_storage / (1024 * 1024)
    total_mb = user_storage.storage_limit / (1024 * 1024)
    percent = (used_mb / total_mb) * 100 if total_mb else 0


    return render(request, 'file_list.html', {
        'documents': documents,
        'used_mb': used_mb,
        'total_mb': total_mb,
        'percent': round(percent, 1)
    })

@email_verified_required
@login_required
def delete_file(request, file_id):
    if request.method == 'DELETE':
        try:
            file = Document.objects.get(id=file_id, user=request.user)
            file_path = file.file.path
            file_size = file.size
            try:
                file.delete()
            except:
                pass
            os.remove(file_path)

            user_storage = request.user.userstorage
            user_storage.used_storage = max(user_storage.used_storage - file_size, 0)
            user_storage.save()

            return JsonResponse({'message' : 'Success.'})
        except Document.DoesNotExist:
            return JsonResponse({'error': 'Error.'}, status=404)

@login_required
def calendar_event_delete(request, event_id):
    if request.method == 'POST':
        event = get_object_or_404(Event, id=event_id, user=request.user)
        try:
            event.delete()
            return JsonResponse({'message': 'Success.'})
        except Exception:
            return JsonResponse({'error': 'Error.'}, status=500)



@email_verified_required
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

@email_verified_required
@login_required
def calendar_events(request):
    events = Event.objects.filter(user=request.user)
    events_data = []
    
    now = timezone.now()
    one_year_from_now = now + timedelta(days=365)
    
    for event in events:
        if event.recurrence == 'none':
            events_data.append({
                "id": event.id,
                "title": event.title,
                "start": event.start_time.isoformat(),
                "end": event.end_time.isoformat(),
                "color": event.color
            })
        else:
            current_date = event.start_time
            end_date = event.recurrence_end
            if end_date:
                end_date = timezone.make_aware(datetime.combine(end_date, datetime.min.time()))
            else:
                end_date = one_year_from_now
            
            while current_date <= end_date:
                event_end = current_date + (event.end_time - event.start_time)
                
                events_data.append({
                    "id": event.id,
                    "title": event.title,
                    "start": current_date.isoformat(),
                    "end": event_end.isoformat(),
                    "color": event.color
                })
                
                if event.recurrence == 'daily':
                    current_date += timedelta(days=1)
                elif event.recurrence == 'weekly':
                    current_date += timedelta(weeks=1)
                elif event.recurrence == 'monthly':
                    if current_date.month == 12:
                        current_date = current_date.replace(year=current_date.year + 1, month=1)
                    else:
                        current_date = current_date.replace(month=current_date.month + 1)
    
    return JsonResponse(events_data, safe=False)

@email_verified_required
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
    

@email_verified_required
@login_required
@ratelimit(key='user', rate='10/m', block=True)
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
    
@email_verified_required
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

@email_verified_required
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


@email_verified_required
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

    
@email_verified_required
@login_required
def pomodoro(request):
    return render(request, "pomodoro.html")

@email_verified_required
@login_required
def add_embed(request):
    if request.method == 'POST':
        url = request.POST["url"]
        embed_info = get_embed_info(url)
        
        if embed_info:
            embed = Embed.objects.create(
                url=url,
                title=embed_info.get("title", "No title"),
                embed_html=embed_info.get("html", ""),
                user=request.user
            )
            return redirect("embed_list")
        else:
            messages.error(request, "Could not generate embed for this URL")
            return redirect("add_embed")
    return render(request, "add_embed.html")

@email_verified_required
@login_required
def embed_list(request):
    embeds = Embed.objects.filter(user=request.user).order_by('order', 'added_at')
    return render(request, "embed_list.html", {"embeds": embeds})

@email_verified_required
@login_required
def delete_embed(request, id):
    if request.method == 'POST':
        embed = get_object_or_404(Embed, id=id, user=request.user)
        try:
            embed.delete()
            return redirect('embed_list')
        except Exception:
            return JsonResponse({'error': 'Error.'}, status=404)
    return JsonResponse({'error': 'Invalid request'}, status=400)
        
@email_verified_required
@login_required
def meeting(request):
    return render(request, 'meeting.html')

@email_verified_required
@login_required
def weather_api(request, location):
    async def fetch_weather_data():
        async with aiohttp.ClientSession() as session:
            geo_url = f'https://nominatim.openstreetmap.org/search?q={location}&format=json'
            headers = {'User-Agent': 'eversync'}
            
            async with session.get(geo_url, headers=headers) as response:
                geo_response = await response.json()
                
                if not geo_response:
                    return {'error': 'Location not found'}, 404

                lat = geo_response[0]["lat"]
                lon = geo_response[0]["lon"]

                weather_url = "https://api.open-meteo.com/v1/forecast"
                params = {
                    "latitude": lat,
                    "longitude": lon,
                    "hourly": "temperature_2m,weathercode,precipitation_probability,wind_speed_10m",
                    "daily": "temperature_2m_max,temperature_2m_min,sunrise,sunset,weathercode",
                    "current_weather": "true",
                    "timezone": "auto"
                }

                async with session.get(weather_url, params=params) as response:
                    weather_response = await response.json()

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
                    return data, 200

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        data, status = loop.run_until_complete(fetch_weather_data())
        loop.close()
        
        if status == 404:
            return JsonResponse(data, status=404)
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': f'Weather service error: {str(e)}'}, status=500)

@email_verified_required
@login_required
@xframe_options_exempt
def weather_view(request, location):
    return render(request, "weather.html", {"location": location})

@email_verified_required
@login_required
def weather_pick(request):
    return render(request, "weather_pick.html")

@email_verified_required
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

@email_verified_required
@login_required
@ratelimit(key='user', rate='10/m', block=True)
def add_task(request):
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.save()
            return redirect('task_list')
    else:
        form = TaskForm()
    return render(request, 'add_task.html', {'form': form})
        
@email_verified_required
@login_required
def task_list(request):
    tasks = Task.objects.filter(user=request.user)
    return render(request, 'task_list.html', {'tasks': tasks})

@email_verified_required
@login_required
def delete_task(request, task_id):
    if request.method == 'POST':
        try:
            task = Task.objects.get(id=task_id, user=request.user)
            task.delete()
            return redirect('task_list')
        except Task.DoesNotExist:
            return JsonResponse({'error': 'Task not found'}, status=404)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@email_verified_required
@login_required
def task_complete(request, task_id):
    if request.method == 'POST':
        try:
            task = Task.objects.get(id=task_id, user=request.user)
            task.completed = not task.completed
            task.save()
            return redirect('task_list')
        except Task.DoesNotExist:
            return JsonResponse({'error': 'Task not found'}, status=404)
    return JsonResponse({'error': 'Invalid request'}, status=400)

def get_affirmation(request):
    try:
        res = requests.get("https://www.affirmations.dev/")
        data = res.json()
        return JsonResponse({"affirmation": data.get("affirmation", "You are enough.")})
    except Exception:
        return JsonResponse({"affirmation": "You're doing great. Keep going!"})

@email_verified_required
@login_required
def thought_reframing(request):
        return render(request, 'thought_reframing.html')

@email_verified_required
@login_required
def documents(request):
    return render(request, "documents.html")


@email_verified_required
@login_required
def save_document(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        title = data.get('title', 'Untitled')
        content = data.get('content', '')

        doc = RichDocument.objects.create(
            title=title,
            content=content,
            owner=request.user
        )
        return JsonResponse({'status': 'success', 'id': doc.id})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@email_verified_required
@login_required
def document_list(request):
    documents = RichDocument.objects.filter(owner=request.user)
    return render(request, 'document_list.html', {'documents': documents})

def delta_to_html(delta_json):
    try:
        delta = json.loads(delta_json)
        html = []
        for op in delta.get('ops', []):
            text = op.get('insert', '')
            if isinstance(text, str):
                # Handle newlines
                if text == '\n':
                    html.append('<br>')
                    continue
                    
                attrs = op.get('attributes', {})
                if attrs:
                    # Handle font sizes
                    if attrs.get('size') == 'huge':
                        text = f'<h1>{text}</h1>'
                    elif attrs.get('size') == 'large':
                        text = f'<h2>{text}</h2>'
                    elif attrs.get('size') == 'small':
                        text = f'<small>{text}</small>'
                    # Handle font family
                    elif attrs.get('font') == 'monospace':
                        text = f'<code>{text}</code>'
                    # Handle text styles
                    elif attrs.get('bold'):
                        text = f'<strong>{text}</strong>'
                    elif attrs.get('italic'):
                        text = f'<em>{text}</em>'
                    elif attrs.get('underline'):
                        text = f'<u>{text}</u>'
                    elif attrs.get('strike'):
                        text = f'<s>{text}</s>'
                    # Handle colors
                    elif attrs.get('color'):
                        text = f'<span style="color: {attrs["color"]}">{text}</span>'
                    elif attrs.get('background'):
                        text = f'<span style="background-color: {attrs["background"]}">{text}</span>'
                    # Handle alignment
                    elif attrs.get('align'):
                        text = f'<div style="text-align: {attrs["align"]}">{text}</div>'
                    # Handle links
                    elif attrs.get('link'):
                        text = f'<a href="{attrs["link"]}">{text}</a>'
                    # Handle code blocks
                    elif attrs.get('code'):
                        text = f'<code>{text}</code>'
                    # Handle blockquotes
                    elif attrs.get('blockquote'):
                        text = f'<blockquote>{text}</blockquote>'
                    # Handle lists
                    elif attrs.get('list') == 'ordered':
                        text = f'<li>{text}</li>'
                    elif attrs.get('list') == 'bullet':
                        text = f'<li>{text}</li>'
                    # Handle indentation
                    elif attrs.get('indent'):
                        text = f'<div style="margin-left: {attrs["indent"] * 2}em">{text}</div>'
                html.append(text)
            elif isinstance(text, dict):
                if text.get('image'):
                    html.append(f'<img src="{text["image"]}" alt="Image">')
        safe_html = bleach.clean(''.join(html), tags=['h1', 'h2', 'small', 'code', 'strong', 'em', 'u', 's', 'span', 'div', 'a', 'blockquote', 'li', 'img', 'br'], attributes={'span': ['style', 'color', 'background-color'], 'div': ['style'], 'a': ['href'], 'img': ['src', 'alt']}, strip=True)
        return safe_html
    except:
        return delta_json

@email_verified_required
@login_required
def view_document(request, doc_id):
    document = get_object_or_404(RichDocument, id=doc_id, owner=request.user)
    html_content = delta_to_html(document.content)
    return render(request, 'view_document.html', {'document': document, 'html_content': html_content})

@email_verified_required
@login_required
def delete_document(request, doc_id):
    if request.method == "POST":
        doc = get_object_or_404(RichDocument, id=doc_id, owner=request.user)
        doc.delete()
    return redirect('document_list')

@email_verified_required
@login_required
def edit_document(request, doc_id):
    document = get_object_or_404(RichDocument, id=doc_id, owner=request.user)
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        document.title = title
        document.content = content
        document.save()
        return redirect('document_list')
    return render(request, 'edit_document.html', {'document': document})

@email_verified_required
@login_required
def get_document(request, id=None):
    doc = get_object_or_404(RichDocument, pk=id, owner=request.user)
    return JsonResponse({"title": doc.title, "content": doc.content})

@email_verified_required
@login_required
@ratelimit(key='user', rate='10/m', block=True)
def send_message(request):
    users = User.objects.exclude(id=request.user.id)
    if request.method == 'POST':
        reciever_username = request.POST.get('receiver')
        content =  request.POST.get('content')
        try:
            receiver = User.objects.get(username=reciever_username)
        except User.DoesNotExist:
            return JsonResponse({"message": "error", "error": "Receiver not found"}, status=404)
        message = Message.objects.create(sender=request.user, receiver=receiver, content=content)
        try:
            user_notifs = UserNotifs.objects.get(user=receiver)
            token = user_notifs.device_token
        except UserNotifs.DoesNotExist:
            token = None
        
        if token:
            title = f"New message from {request.user.username}"
            body = content[:100]
            send_push_notification(token, title, body)
        
        return JsonResponse({"message": "sent", "message_id": message.id})
    else:
        return JsonResponse({"message": "error"})
    
@email_verified_required
@login_required
def inbox(request):
    messages = Message.objects.filter(receiver=request.user).select_related('sender', 'receiver').order_by("-timestamp")
    has_unseen = messages.filter(seen=False).exists()
    data = [{
        "sender": msg.sender.username,
        "content": msg.content,
        "timestamp": msg.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "id": msg.id
    } for msg in messages]
    return JsonResponse({"messages": data, "has_unseen": has_unseen})

@email_verified_required
@login_required
def sent_messages(request):
    messages = Message.objects.filter(sender=request.user).select_related('receiver').order_by("-timestamp")
    data = [{
        "receiver": msg.receiver.username,
        "content": msg.content,
        "timestamp": msg.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "id": msg.id
    } for msg in messages]
    return JsonResponse({"messages": data})
    
@email_verified_required
@login_required
def chat_page(request):
    sent = Message.objects.filter(sender=request.user).values_list('receiver', flat=True)
    received = Message.objects.filter(receiver=request.user).values_list('sender', flat=True)
    user_ids = set(sent) | set(received)
    users = User.objects.filter(id__in=user_ids).exclude(id=request.user.id)

    users_with_unseen = []
    for user in users:
        unseen_count = Message.objects.filter(
            sender=user,
            receiver=request.user,
            seen=False
        ).count()
        users_with_unseen.append({
            'username': user.username,
            'unseen_count': unseen_count
        })
    return render(request, 'chat.html', {'users': users_with_unseen})

@email_verified_required
@login_required
def delete_message(request, message_id):
    if request.method == "POST":
        message = get_object_or_404(Message, id=message_id, sender=request.user)
        message.delete()
        referer = request.META.get("HTTP_REFERER")
    return redirect(referer)

@email_verified_required
@login_required
def music(request):
    return render(request, 'music.html') 

@email_verified_required
@login_required
def stream_song(request):
    query = request.GET.get("query")
    if not query:
        return JsonResponse({"error": "No search query provided"}, status=400)

    with tempfile.TemporaryDirectory() as tmpdir:
        ytpdl_options = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'noplaylist': 'true',
            'outtmpl': f'{tmpdir}/%(title)s.%(ext)s',
            'postprocessors': [],
            'quiet': True,
            'cookiefile': '/code/cookies.txt'
        }

        with YoutubeDL(ytpdl_options) as ytpdl:
            info = ytpdl.extract_info(f"ytsearch1:{query} topic", download=True)
            filepath = ytpdl.prepare_filename(info['entries'][0]).replace('.webm', '.mp3')
        return FileResponse(open(filepath, 'rb'), content_type='audio/mpeg')

@email_verified_required
@login_required       
def get_thumbnail(request):
    query = request.GET.get("query")
    if not query:
        return JsonResponse({"error": "No search query provided"}, status=400)

    ytdlp_opts = {
        'quiet': True,
        'skip_download': True,
        'format': 'bestaudio/best',
        'noplaylist': True,
        'default_search': 'ytsearch1',
        'cookiefile': '/code/cookies.txt'
    }

    with YoutubeDL(ytdlp_opts) as ydl:
        info = ydl.extract_info(f"ytsearch1:{query} topic", download=False)
        video_info = info['entries'][0]
        thumbnail_url = video_info.get('thumbnail')
        title = video_info.get('title')

    return JsonResponse({
        "thumbnail": thumbnail_url,
        "title": title
    })

@email_verified_required
@login_required
def chat_with_user(request, username):
    if username == request.user.username:
        return redirect('chat_page')
    other_user = get_object_or_404(User, username=username)
    messages = Message.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user, receiver=request.user)
    ).select_related('sender', 'receiver').prefetch_related('reactions__user').order_by('timestamp')
    pinned_message = Message.objects.filter(pinned=True, sender=request.user).order_by('-timestamp').first()
    Message.objects.filter(sender=other_user, receiver=request.user, seen=False).update(seen=True, seen_at=now())

    return render(request, 'chat_thread.html', {
        'messages': messages,
        'other_user': other_user,
        'pinned_message': pinned_message
    })
@email_verified_required
@login_required
def whiteboard_view(request, whiteboard_id=None):
    if whiteboard_id:
        whiteboard = get_object_or_404(Whiteboard, id=whiteboard_id, owner=request.user)
        strokes = Stroke.objects.filter(whiteboard=whiteboard).order_by('created_at')
        
        # Process images to include full URLs
        images = []
        for img_data in whiteboard.images:
            if isinstance(img_data, dict) and 'id' in img_data:
                img_data['url'] = request.build_absolute_uri(settings.MEDIA_URL + img_data['id'])
                images.append(img_data)
        
        images_json = json.dumps(images)
        stroke_data = [stroke.data for stroke in strokes]
        context = {
            'whiteboard': whiteboard,
            'strokes_json': json.dumps(stroke_data),
            'images_json': images_json
        }
        return render(request, 'whiteboard.html', context)
    else:
        whiteboards = Whiteboard.objects.filter(owner=request.user)
        context = {
            'whiteboards': whiteboards,
        }
        return render(request, 'whiteboard_list.html', context)
@email_verified_required
@login_required
def save_stroke(request, whiteboard_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            stroke_data = data.get('stroke')
            
            if not stroke_data:
                return JsonResponse({'error': 'No stroke data provided'}, status=400)
            
            whiteboard = Whiteboard.objects.get(id=whiteboard_id, owner=request.user)

            stroke = Stroke.objects.create(
                whiteboard=whiteboard,
                user=request.user,
                data=stroke_data
            )
            whiteboard.save()
            return JsonResponse({'status': 'success'})
        except Whiteboard.DoesNotExist:
            return JsonResponse({'error': 'Whiteboard not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)

@email_verified_required
@login_required
def create_whiteboard(request):
    if request.method == 'POST':
        name = request.POST.get('name', 'Untitled Whiteboard')
        new_board = Whiteboard.objects.create(owner=request.user, title=name)
        return redirect('whiteboard', whiteboard_id=new_board.id)
    return render(request, 'create_whiteboard.html')

@email_verified_required
@login_required
def delete_stroke(request, whiteboard_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            index = data.get('index')

            whiteboard = Whiteboard.objects.get(id=whiteboard_id, owner=request.user)
            strokes = Stroke.objects.filter(whiteboard=whiteboard).order_by('created_at')

            stroke_to_delete = strokes[index]
            stroke_to_delete.delete()

            fs = FileSystemStorage()
            for img_data in whiteboard.images:
                if isinstance(img_data, dict) and 'id' in img_data:
                    try:
                        fs.delete(f'whiteboard_images/{img_data["id"]}')
                    except:
                        pass
            
            whiteboard.images = []
            whiteboard.save()


            return JsonResponse({'success': True})
        except Whiteboard.DoesNotExist:
            return JsonResponse({'error': 'Whiteboard not found'}, status=404)
        except IndexError:
            return JsonResponse({'error': 'Invalid stroke index'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@email_verified_required
@login_required     
def delete_all_strokes(request, whiteboard_id):
    if request.method == 'POST':
        try:
            whiteboard = Whiteboard.objects.get(id=whiteboard_id, owner=request.user)
            Stroke.objects.filter(whiteboard=whiteboard).delete()
            
            fs = FileSystemStorage()
            for img_data in whiteboard.images:
                if isinstance(img_data, dict) and 'id' in img_data:
                    try:
                        fs.delete(f'whiteboard_images/{img_data["id"]}')
                    except:
                        pass
            
            whiteboard.images = []
            whiteboard.save()            
            return JsonResponse({'success': True})
        except Whiteboard.DoesNotExist:
            return JsonResponse({'error': 'Whiteboard not found'}, status=404)


@email_verified_required
@login_required
def delete_whiteboard(request, whiteboard_id):
    whiteboard = get_object_or_404(Whiteboard, id=whiteboard_id, owner=request.user)
    if request.method == 'POST':
        whiteboard.delete()
        return redirect('whiteboard') 
    return redirect('whiteboard')


User = get_user_model()

@login_required
def verify_email(request):
    token = request.GET.get('token')
    if not token:
        return HttpResponse("Invalid verification link.", status=400)
    
    email = verify_token(token)
    if not email:
        return HttpResponse("Verification link expired or invalid.", status=400)
    
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return HttpResponse("User not found.", status=404)


    email_address, created = EmailAddress.objects.get_or_create(user=user, email=email)
    email_address.verified = True
    email_address.primary = True
    email_address.save()
    
    return HttpResponse("Email verified successfully! You can now log in.")

@login_required
def update_email(request):
# if request.user.email:
#    return redirect('/')
    
    if request.method == 'POST':
        form = EmailUpdateForm(request.POST)
        if form.is_valid():
            request.user.email = form.cleaned_data['email']
            request.user.save()
            send_email_confirmation(request, request.user)
            return redirect('account_email_verification_sent')
    else:
        form = EmailUpdateForm()

    return render(request, 'account/update_email.html', {'form': form}) 

@login_required
def login_redirect(request):
    user = request.user

    if not user.email:
        return redirect('update_email') 

    if not EmailAddress.objects.filter(user=user, email=user.email, verified=True).exists():
        return redirect('account_email_verification_sent')

    return redirect('/') 

@email_verified_required
@login_required
@ratelimit(key='user', rate='20/m', block=True)
def pin_message(request, message_id):
    msg = get_object_or_404(Message, id=message_id)
    
    Message.objects.filter(sender=request.user, pinned=True).update(pinned=False)
    
    msg.pinned = not msg.pinned
    msg.save()
    return redirect('chat_with_user', username=msg.receiver.username if msg.sender == request.user else msg.sender.username)

@email_verified_required
@login_required
def save_images(request, whiteboard_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            images = data.get('images', [])
            whiteboard = Whiteboard.objects.get(id=whiteboard_id)
            whiteboard.images = images
            whiteboard.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid method'})

@email_verified_required
@login_required
@ratelimit(key='user', rate='20/m', block=True)
def upload_image(request, whiteboard_id):
    if request.method == 'POST':
        try:
            whiteboard = Whiteboard.objects.get(id=whiteboard_id, owner=request.user)
            image = request.FILES.get('image')
            
            if not image:
                return JsonResponse({'error': 'No image provided'}, status=400)
                
            # Generate a unique filename
            ext = os.path.splitext(image.name)[1]
            filename = f'whiteboard_{whiteboard_id}_{uuid.uuid4().hex}{ext}'
            
            # Save the image
            fs = FileSystemStorage()
            filename = fs.save(f'whiteboard_images/{filename}', image)
            image_url = fs.url(filename)
            
            return JsonResponse({
                'success': True,
                'image_url': image_url,
                'image_id': filename
            })
            
        except Whiteboard.DoesNotExist:
            return JsonResponse({'error': 'Whiteboard not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@email_verified_required
@login_required
def delete_image(request, whiteboard_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            image_id = data.get('image_id')
            
            if not image_id:
                return JsonResponse({'error': 'No image ID provided'}, status=400)
            
            whiteboard = Whiteboard.objects.get(id=whiteboard_id, owner=request.user)
            
            whiteboard.images = [img for img in whiteboard.images if img.get('id') != image_id]
            whiteboard.save()
            
            fs = FileSystemStorage()
            try:
                fs.delete(f'whiteboard_images/{image_id}')
            except:
                pass  
                
            return JsonResponse({'success': True})
            
        except Whiteboard.DoesNotExist:
            return JsonResponse({'error': 'Whiteboard not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'Invalid request method'}, status=405)


def update_device_token(request):
    try:
        data = json.loads(request.body)
        token = data.get('device_token', '').strip()
        if not token:
            return JsonResponse({"error": "No device_token provided"}, status=400)

        user_notifs, created = UserNotifs.objects.get_or_create(user=request.user)
        user_notifs.device_token = token
        user_notifs.save()

        return JsonResponse({"message": "Device token updated"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
@email_verified_required
@login_required
@ratelimit(key='user', rate='3/m', block=True)
def save_web_archive(request):
    if request.method == 'POST':
        form = WebArchiveForm(request.POST)
        if form.is_valid():
            driver = None
            try:
                # Set up Chrome options
                chrome_options = Options()
                for arg in SELENIUM_CHROME_ARGS:
                    chrome_options.add_argument(arg)
                chrome_options.add_experimental_option("prefs", SELENIUM_CHROME_PREFS)
                # Initialize Chrome driver
                driver = webdriver.Chrome(options=chrome_options)
                url = form.cleaned_data['url']
                print(f"Attempting to access URL: {url}")
                
                driver.get(url)

                # try:
                #     cookie_button = WebDriverWait(driver, 5).until(
                #         EC.element_to_be_clickable((
                #             By.XPATH,
                #             "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept') or " +
                #             "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree') or " +
                #             "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'allow')]"))
                #     )
                #     cookie_button.click()
                #     WebDriverWait(driver, 5).until_not(EC.presence_of_element_located((By.XPATH,
                #                                 "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept') or " +
                #                                 "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree') or " +
                #                                 "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'allow')]"))
                #     )
                # except:
                #     print("No cookie banner found or clickable :3")
                WebDriverWait(driver, 5).until(
                    lambda driver: driver.execute_script('return document.readyState') == 'complete'
                )

                # Get page title and content
                title = driver.title or url
                
                content = driver.execute_script("""
                    return new XMLSerializer().serializeToString(document);
                """)
                
                print(f"Page title: {title}")
                
                # Take screenshot
                screenshot = driver.get_screenshot_as_png()
                print("Screenshot taken successfully")
                
                # Create archive instance with user
                archive = form.save(commit=False)
                archive.user = request.user
                archive.title = title
                archive.content = content
                archive.save()
                print("Archive saved successfully")
                
                # Now save the screenshot
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    tmp.write(screenshot)
                    print(f"Saving screenshot to: {tmp.name}")
                    archive.screenshot.save(f'archive_{archive.id}.png', File(open(tmp.name, 'rb')))
                    archive.save()
                
                messages.success(request, "Page archived successfully!")
                return redirect('web_archive')
                
            except Exception as e:
                print(f"Error in save_web_archive: {str(e)}")
                messages.error(request, f"Error archiving page: {str(e)}")
                return redirect('web_archive')
            finally:
                if driver:
                    try:
                        driver.quit()
                        print("Chrome driver closed successfully")
                    except Exception as e:
                        print(f"Error closing Chrome driver: {str(e)}")
    else:
        form = WebArchiveForm()
    return render(request, 'save_web_archive.html', {'form': form})

@email_verified_required
@login_required
def web_archive(request):
    archives = WebArchive.objects.filter(user=request.user)
    return render(request, 'web_archive.html', {'archives': archives})

@email_verified_required
@login_required
def delete_web_archive(request, archive_id):
    if request.method == 'POST':
        archive = get_object_or_404(WebArchive, id=archive_id, user=request.user)
        try:
            if archive.screenshot:
                try:
                    archive.screenshot.delete()
                except:
                    pass 
            
            archive.delete()
            
        except Exception as e:
            messages.error(request, f"Error deleting archive: {str(e)}")
            
    return redirect('web_archive')

@email_verified_required
@login_required
def view_web_archive(request, archive_id):
    archive = get_object_or_404(WebArchive, id=archive_id, user=request.user)
    return render(request, 'view_web_archive.html', {'archive': archive})

@email_verified_required
@login_required
def update_profile_picture(request):
    if request.method == 'POST':
        if 'profile_picture' in request.FILES:
            if request.user.profile.profile_picture:
                request.user.profile.profile_picture.delete()
            
            request.user.profile.profile_picture = request.FILES['profile_picture']
            request.user.profile.save()
            messages.success(request, "Profile picture updated successfully!")
        else:
            messages.error(request, "No image file provided.")
    return redirect('manage')

@login_required
def delete_profile_picture(request):
    if request.method == 'POST':
        profile = request.user.profile
        if profile.profile_picture:
            profile.profile_picture.delete()
            profile.save()
            messages.success(request, "Profile picture deleted successfully!")
        else:
            messages.error(request, "No profile picture to delete.")
    return redirect('manage')

@email_verified_required
@login_required
def reorder_embeds(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            embed_ids = data.get('embed_ids', [])
            for idx, embed_id in enumerate(embed_ids):
                try:
                    embed = Embed.objects.get(id=embed_id, user=request.user)
                    embed.order = idx
                    embed.save()
                except Embed.DoesNotExist:
                    continue
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

@email_verified_required
@login_required
@ratelimit(key='user', rate='20/m', block=True)
def add_reaction(request, message_id):
    if request.method == 'POST':
        reaction_type = request.POST.get('reaction_type')
        if not reaction_type:
            return JsonResponse({'error': 'No reaction_type provided'}, status=400)
        message = get_object_or_404(Message, id=message_id)
        reaction, created = MessageReaction.objects.get_or_create(
            message=message,
            user=request.user,
            reaction_type=reaction_type
        )
        return JsonResponse({'success': True, 'created': created})
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@email_verified_required
@login_required
def remove_reaction(request, message_id):
    if request.method == 'POST':
        reaction_type = request.POST.get('reaction_type')
        if not reaction_type:
            return JsonResponse({'error': 'No reaction_type provided'}, status=400)
        message = get_object_or_404(Message, id=message_id)
        if not (message.sender == request.user or message.receiver == request.user):
            return JsonResponse({'error': 'Permission denied'}, status=403)
        try:
            reaction = MessageReaction.objects.get(
                message=message,
                user=request.user,
                reaction_type=reaction_type
            )
            reaction.delete()
            return JsonResponse({'success': True})
        except MessageReaction.DoesNotExist:
            return JsonResponse({'error': 'Reaction not found'}, status=404)
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@email_verified_required
@login_required
def edit_message(request, message_id):
    if request.method == "POST":
        message = get_object_or_404(Message, id=message_id, sender=request.user)
        new_content = request.POST.get("content", "").strip()
        if not new_content:
            return JsonResponse({"error": "Content cannot be empty."}, status=400)
        message.content = new_content
        message.save()
        return JsonResponse({"success": True, "content": message.content})
    return JsonResponse({"error": "Invalid request method"}, status=405)

