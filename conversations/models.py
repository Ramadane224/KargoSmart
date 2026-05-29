from django.conf import settings
from django.db import models


class Conversation(models.Model):
    """Canal de discussion lié à une livraison."""
    
    livraison = models.OneToOneField(
        'livraisons.Livraison',
        on_delete=models.CASCADE,
        related_name='conversation'
    )
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='conversations',
        help_text="Gestionnaire, Client, Livreur assigné"
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_derniere_activite = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ks_messages_conversation'
        ordering = ['-date_derniere_activite']

    def __str__(self):
        return f"Discussion {self.livraison.code_livraison}"


class Message(models.Model):
    """Message dans une conversation."""
    
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='messages_envoyes'
    )
    contenu = models.TextField()
    est_lu = models.BooleanField(default=False)
    date_envoi = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ks_messages_message'
        ordering = ['date_envoi']

    def __str__(self):
        return f"{self.auteur} — {self.date_envoi.strftime('%d/%m/%Y %H:%M')}"


class LectureMessage(models.Model):
    """Suivi de lecture pour chaque participant."""
    
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='lectures'
    )
    lecteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    date_lecture = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ks_messages_lecture_message'
        unique_together = ('message', 'lecteur')

    def __str__(self):
        return f"{self.lecteur} a lu {self.message}"
