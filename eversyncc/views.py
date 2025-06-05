from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, FileResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm
# Create your views here.
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.contrib.auth.views import PasswordChangeView
from .forms import UsernameChangeForm, DocumentForm, EventForm, NoteForm, TaskForm
from .models import Document, Event, Notes, Embed, Task, RichDocument, Message
from django.contrib import messages
from allauth.account.views import LoginView as AllauthLoginView
import os
from pathlib import Path
from eversyncc.models import UserNotifs
import requests
from allauth.account.models import EmailAddress
from django.views.decorators.clickjacking import xframe_options_exempt
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
from .forms import EmailUpdateForm
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
            filename = document.file.name
            ext = os.path.splitext(filename)[1].lower()
            file_size = document.file.size


            forbidden_extensions=['.html','.htm','.php','.exe','.js','.sh','.bat']
            if ext in forbidden_extensions:
                request.session.flush()
                logout(request)
                return HttpResponse("<html><body><script>alert('Uploading possibly malicious files is forbidden. You have been logged out.'); location.reload();</script></body></html>")
            user_storage = request.user.userstorage
            if user_storage.used_storage + file_size > user_storage.storage_limit:
              return HttpResponse(
                    "<html><body><script>alert('Upload blocked: Storage limit exceeded. Please delete files.'); window.history.back();</script></body></html>"
                )
            
            document.user = request.user
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
        try:
            event = Event.objects.get(id=event_id)
            try:
                event.delete()
                return JsonResponse({'messsage': 'Success.'})
            except:
                return JsonResponse({'error': 'Error.'}, status=404)
        except:
            return JsonResponse({'error': 'Error.'}, status=404)



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
                embed_html=embed_info.get("html", "")
            )
            return redirect("embed_list")
        else:
            messages.error(request, "Could not generate embed for this URL")
            return redirect("add_embed")
    return render(request, "add_embed.html")

@email_verified_required
@login_required
def embed_list(request):
    embeds = Embed.objects.all()
    return render(request, "embed_list.html", {"embeds": embeds})

@email_verified_required
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


@email_verified_required
@login_required
def view_document(request, doc_id):
    document = get_object_or_404(RichDocument, id=doc_id, owner=request.user)
    return render(request, 'view_document.html', {'document': document})

@email_verified_required
@login_required
def delete_document(request, doc_id):
    if request.method == "POST":
        doc = get_object_or_404(RichDocument, id=doc_id, owner=request.user)
        doc.delete()
    return redirect('document_list')

@email_verified_required
@login_required
def get_document(request, id=None):
    try:
        doc = RichDocument.objects.get(pk=id)
        return JsonResponse({"title": doc.title, "content": doc.content})
    except RichDocument.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)
    
@email_verified_required
@login_required
def send_message(request):
    users = User.objects.exclude(id=request.user.id)
    if request.method == 'POST':
        reciever_username = request.POST.get('receiver')
        content =  request.POST.get('content')
        receiver = User.objects.get(username=reciever_username)
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
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }],
            'quiet': True,
            'cookiefile': '/code/cookies.txt'
        }

        with YoutubeDL(ytpdl_options) as ytpdl:
            info = ytpdl.extract_info(f"ytsearch1:{query} topic", download=True)
            filepath = ytpdl.prepare_filename(info['entries'][0]).replace('.webm', '.mp3').replace('.m4a', '.mp3')
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
    other_user = User.objects.get(username=username)
    messages = Message.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user, receiver=request.user)
    ).select_related('sender', 'receiver').order_by('timestamp')
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
            stroke_points = data.get('stroke') 
            
            if not stroke_points:
                return JsonResponse({'error': 'No stroke data provided'}, status=400)
            
            whiteboard = Whiteboard.objects.get(id=whiteboard_id, owner=request.user)

            Stroke.objects.create(
                whiteboard=whiteboard,
                user=request.user,
                data=stroke_points
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

            whiteboard = Whiteboard.objects.get(id=whiteboard_id)
            strokes = Stroke.objects.filter(whiteboard=whiteboard).order_by('created_at')

            stroke_to_delete = strokes[index]
            stroke_to_delete.delete()
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