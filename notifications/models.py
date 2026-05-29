from django.conf import settings
from django.db import models


class TypeNotification(models.TextChoices):
    LIVRAISON_ASSIGNEE = 'ASSIGNEE', 'Livraison assignée'
    LIVRAISON_EN_COURS = 'EN_COURS', 'Livraison en cours'
    LIVRAISON_TERMINEE = 'TERMINEE', 'Livraison terminée'
    LIVRAISON_ANNULEE = 'ANNULEE', 'Livraison annulée'
    SYSTEME = 'SYSTEME', 'Notification système'
    ALERTE_ADMIN = 'ALERTE', 'Alerte administrateur'


class Notification(models.Model):
    destinataire = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    livraison = models.ForeignKey(
        'livraisons.Livraison',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    type_notif = models.CharField(max_length=20, choices=TypeNotification.choices)
    titre = models.CharField(max_length=200)
    message = models.TextField()
    est_lue = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ks_notifications_notification'
        ordering = ['-date_creation']

    def __str__(self):
        return f"{self.titre} ({self.get_type_notif_display()})"
