from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

# Create your models here.
from django.contrib.auth.models import User

class UserNotifs(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    device_token = models.CharField(blank=True, null=True)

def __str__(self):
    token = self.device_token[:8] if self.device_token else "None"
    return f"{self.user.username}'s notif token: {token}..."

class UserStorage(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    storage_limit = models.BigIntegerField(default=5 * 1024 * 1024 * 1024)  # 5 GB
    used_storage = models.BigIntegerField(default=0)
    email_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.used_storage} / {self.storage_limit} bytes"

class Document(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=500)
    file = models.FileField(upload_to="", max_length=500)
    size = models.BigIntegerField(default=0)

    def save(self, *args, **kwargs):
        if self.file:
            self.size = self.file.size  # automatically update size on save
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class Event(models.Model):
    RECURRENCE_CHOICES = [
        ('none', 'None'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    color = models.TextField(default='#3788d8')
    recurrence = models.CharField(max_length=10, choices=RECURRENCE_CHOICES, default='none')
    recurrence_end = models.DateField(null=True, blank=True)

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
    title = models.CharField()
    provider = models.CharField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True) 
    embed_html = models.TextField()
    added_at = models.DateField(auto_now_add=True)
    order = models.IntegerField(default=0)

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
    
class RichDocument(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.title
    
class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    seen = models.BooleanField(default=False)
    seen_at = models.DateTimeField(null=True, blank=True)
    pinned = models.BooleanField(default=False)

    def __str__(self):
        return f"From {self.sender} to {self.receiver} at {self.timestamp}"
    
class Thread(models.Model):
    participants = models.ManyToManyField(User)

    def __str__(self):
        return " / ".join([u.username for u in self.participants.all()])
    
class Whiteboard(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    images = models.JSONField(default=list, blank=True)  
    
class Stroke(models.Model):
    whiteboard = models.ForeignKey(Whiteboard, related_name='strokes', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

class WebArchive(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE) 
    url = models.URLField()  
    title = models.CharField(max_length=255)  
    screenshot = models.ImageField(upload_to='web_archives/')
    content = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

class MessageReaction(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reaction_type = models.CharField(max_length=16)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('message', 'user', 'reaction_type')

    def __str__(self):
        return f"{self.user.username} reacted {self.reaction_type} to message {self.message.id}"