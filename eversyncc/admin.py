from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.contrib.auth.models import User

from eversyncc.models import Event, Document, Notes, Embed, Task, RichDocument, UserNotifs, UserStorage, Message, Thread, Whiteboard, Stroke, WebArchive, Profile

class EventInline(admin.TabularInline):
    model = Event
    extra = 0

class DocumentInline(admin.TabularInline):
    model = Document
    extra = 0

class NotesInline(admin.TabularInline):
    model = Notes
    extra = 0

class EmbedInline(admin.TabularInline):
    model = Embed
    extra = 0

class TaskInline(admin.TabularInline):
    model = Task
    extra = 0

class RichDocumentInline(admin.TabularInline):
    model = RichDocument
    extra = 0

class UserNotifsInline(admin.TabularInline):
    model = UserNotifs
    extra = 0

class UserStorageInline(admin.TabularInline):
    model = UserStorage
    extra = 0

class MessageInline(admin.TabularInline):
    model = Message
    fk_name = 'sender'
    extra = 0

class WebArchiveInline(admin.TabularInline):
    model = WebArchive
    extra = 0

class WhiteboardInline(admin.TabularInline):
    model = Whiteboard
    extra = 0

class ProfileInline(admin.TabularInline):
    model = Profile
    extra = 0

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'size')
    search_fields = ('title', 'user__username')

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'start_time', 'end_time', 'recurrence')
    search_fields = ('title', 'user__username')
    list_filter = ('recurrence', 'user')

@admin.register(Notes)
class NotesAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'created_at')
    search_fields = ('title', 'user__username')

@admin.register(Embed)
class EmbedAdmin(admin.ModelAdmin):
    list_display = ('title', 'provider', 'user', 'added_at')
    search_fields = ('title', 'provider', 'user__username')

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'completed', 'due_date')
    search_fields = ('title', 'user__username')
    list_filter = ('completed',)

@admin.register(RichDocument)
class RichDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'created_at', 'updated_at')
    search_fields = ('title', 'owner__username')

@admin.register(UserNotifs)
class UserNotifsAdmin(admin.ModelAdmin):
    list_display = ('user', 'device_token')

@admin.register(UserStorage)
class UserStorageAdmin(admin.ModelAdmin):
    list_display = ('user', 'used_storage', 'storage_limit', 'email_verified')
    list_filter = ('email_verified',)

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'timestamp', 'seen', 'pinned')
    search_fields = ('sender__username', 'receiver__username', 'content')
    list_filter = ('seen', 'pinned')

@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ('id',)
    filter_horizontal = ('participants',)

@admin.register(Whiteboard)
class WhiteboardAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'created_at', 'updated_at')
    search_fields = ('title', 'owner__username')

@admin.register(Stroke)
class StrokeAdmin(admin.ModelAdmin):
    list_display = ('whiteboard', 'user', 'created_at')

@admin.register(WebArchive)
class WebArchiveAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'created_at')
    search_fields = ('title', 'user__username')

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user',)

admin.site.unregister(User)

@admin.register(User)
class CustomUserAdmin(DefaultUserAdmin):
    inlines = [
        EventInline,
        DocumentInline,
        NotesInline,
        EmbedInline,
        TaskInline,
        RichDocumentInline,
        MessageInline,
        WebArchiveInline,
        WhiteboardInline,
        ProfileInline,
        UserNotifsInline,
        UserStorageInline
    ]