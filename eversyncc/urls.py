from django.urls import path
from . import views
from .views import RedirectFromLogin, thought_reframing, sent_messages, chat_page, inbox, send_message, document_list, save_document, documents, get_affirmation, weather_pick, weather_view, weather_api, meeting, delete_embed, pomodoro, upload_file, add_embed, embed_list, file_list, delete_file, calendar, calendar_events, calendar_event_create, calendar_event_delete, note_add, note_list, notes
from django.conf import settings
from django.conf.urls.static import static



urlpatterns = [
    path('', views.index, name='index'),
    path('logoutz/', views.logout_view, name='logoutz'),
    path('register/', views.register, name='register'),
    path('manage/', views.manage, name='manage'),
    path('change_username/', views.change_username, name="change_username"),
    path('change_password/', views.change_password, name="change_password"),
    path("accounts/login/", RedirectFromLogin.as_view(), name="login"),
    path('upload/', upload_file, name='upload_file'),
    path('file_list/', file_list, name='file_list'),
    path('delete_file/<int:file_id>', delete_file, name='delete_file'),
    path('calendar/', calendar, name="calendar"),
    path('calendar/events/', calendar_events, name="calendar_events"),
    path('calendar_event_create/', calendar_event_create, name="calendar_event_create"),
    path('calendar_event_delete/<int:event_id>', calendar_event_delete, name="calendar_event_delete"),
    path('note_add/', note_add, name="note_add"),
    path('note_list/', note_list, name="note_list"),
    path('notes/', notes, name="notes"),
    path('pomodoro/', pomodoro, name="pomodoro"),
    path('add_embed/', add_embed, name="add_embed"),
    path('embed_list/', embed_list, name="embed_list"),
    path('delete_embed/<int:id>/', delete_embed, name="delete_embed"),
    path('meeting', meeting,  name="meeting"),
    path('weather_api/<str:location>', weather_api, name="weather_api"),
    path('weather/<str:location>/', weather_view, name="weather_view"),
    path('weather_pick', weather_pick, name="weather_pick"),
    path('note_delete/<int:note_id>/', views.note_delete, name='note_delete'),
    path('download_calendar/<int:event_id>/', views.download_calendar, name='download_calendar'),
    path('add_task/', views.add_task, name='add_task'),
    path('task_list/', views.task_list, name='task_list'),
    path('delete_task/<int:task_id>/', views.delete_task, name='delete_task'),
    path('task_complete/<int:task_id>/', views.task_complete, name='task_complete'),
    path("api/affirmation/", get_affirmation, name="get_affirmation"),
    path("thought_reframing", thought_reframing, name="thought_reframing"),
    path("documents/new", views.documents, name="documents"),
    path("documents", views.document_list, name="document_list"),
    path('save-document/', views.save_document, name='save_document'),
    path('documents/<int:doc_id>/', views.view_document, name='view_document'),
    path('documents/<int:doc_id>/delete/', views.delete_document, name='delete_document'),
    path('send/', views.send_message, name='send_message'),
    path('inbox/', views.inbox, name='inbox'),
    path('outbox/', views.sent_messages, name="outbox"),
    path('chat', views.chat_page, name="chat"),
    path('delete/<int:message_id>/', views.delete_message, name='delete_message'),
    path('stream_song/', views.stream_song, name='stream_song'),
    path('music', views.music, name="music"),
    path('get_thumbnail/', views.get_thumbnail, name='get_thumbnail'),
    path('chat/<str:username>/', views.chat_with_user, name='chat_with_user'),
    path('whiteboard/<int:whiteboard_id>/save-stroke/', views.save_stroke, name='save_stroke'),
    path('whiteboard/', views.whiteboard_view, name='whiteboard'),
    path('whiteboard/create/', views.create_whiteboard, name='create_whiteboard'),
    path('whiteboard/<int:whiteboard_id>/', views.whiteboard_view, name='whiteboard'),
    path('whiteboard/<int:whiteboard_id>/delete-stroke/', views.delete_stroke, name='delete_stroke'),
    path('whiteboard/<int:whiteboard_id>/delete-all-strokes/', views.delete_all_strokes, name='delete_all_strokes'),
    path('whiteboard/delete/<int:whiteboard_id>/', views.delete_whiteboard, name='delete_whiteboard'),
    path('delete_account/', views.delete_account, name="delete_account"),
    path('verify-email/', views.verify_email, name='verify_email'),
    path('update-email/', views.update_email, name='update_email'),
    path('redirect-after-login/', views.login_redirect, name='login_redirect'),
    path('pin/<int:message_id>/', views.pin_message, name='pin_message'),




]

if settings.DEBUG:
       urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)