from django.urls import path
from . import views
from .views import RedirectFromLogin, pomodoro, upload_file, add_embed, embed_list, file_list, delete_file, calendar, calendar_events, calendar_event_create, calendar_event_delete, note_add, note_list, notes
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
    path('embed_list/', embed_list, name="embed_list")
]

if settings.DEBUG:
       urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)