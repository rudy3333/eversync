from django.apps import AppConfig


class EversynccConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'eversyncc'

    def ready(self):
        import eversyncc.signals