# Generated by Django 5.2.1 on 2025-05-27 17:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eversyncc', '0010_task_due_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='task',
            name='title',
            field=models.CharField(),
        ),
    ]
