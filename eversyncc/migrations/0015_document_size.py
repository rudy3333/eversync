# Generated by Django 5.2.1 on 2025-05-30 23:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eversyncc', '0014_userstorage'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='size',
            field=models.BigIntegerField(default=0),
        ),
    ]
