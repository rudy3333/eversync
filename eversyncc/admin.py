from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.contrib.auth.models import User

from eversyncc.models import Event, Document, Notes, Embed, Task, RichDocument

admin.site.register(Document)
admin.site.register(Event)
admin.site.register(Notes)
admin.site.register(Embed)
admin.site.register(Task)
admin.site.register(RichDocument)

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
    ]