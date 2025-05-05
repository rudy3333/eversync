from django.db import models

# Create your models here.
from django.contrib.auth.models import User

class Document(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    file = models.FileField(upload_to="files/files")

    def __str__(self):
        return self.title
