from django.apps import AppConfig


class LivraisonsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'livraisons'

    def ready(self):
        import livraisons.signals  # noqa: F401
