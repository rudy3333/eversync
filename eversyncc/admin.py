from django.contrib import admin
from .models import Document, Event, Notes, Embed

# Register your models here.

admin.site.register(Document)
admin.site.register(Event)
admin.site.register(Notes)
admin.site.register(Embed)