from django.db import models

# Create your models here.
from django.contrib.auth.models import User

class Document(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    file = models.FileField(upload_to="")

    def __str__(self):
        return self.title

class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    color = models.TextField(default='#3788d8')

    def __str__(self):
        return self.title

class Notes(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateField(auto_now_add=True)
    
    def __str__(self):
        return self.title
    
class Embed(models.Model):
    url = models.URLField()
    title = models.CharField(max_length=200)
    provider = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True) 
    embed_html = models.TextField()
    added_at = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.title
    
class Task(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField()
    created_at = models.DateField(auto_now_add=True)
    completed = models.BooleanField(default=False)
    due_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.title