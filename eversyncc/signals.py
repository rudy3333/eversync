from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserStorage, UserNotifs

@receiver(post_save, sender=User)
def create_user_storage(sender, instance, created, **kwargs):
    if created:
        UserStorage.objects.create(user=instance)
        UserNotifs.objects.create(user=instance)