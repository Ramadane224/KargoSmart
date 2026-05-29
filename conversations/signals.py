from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from livraisons.models import Livraison
from .models import Conversation


@receiver(post_save, sender=Livraison)
def creer_conversation_livraison(sender, instance, created, **kwargs):
    """Auto-crée une conversation quand une livraison est créée."""
    if created:
        conversation = Conversation.objects.create(livraison=instance)
        
        # Ajouter participants: gestionnaire/créateur (toujours)
        participants = [instance.createur]
        
        # Ajouter le client s'il a un profil utilisateur enregistré
        try:
            from utilisateurs.models import Profil
            client_profil = Profil.objects.get(email=instance.client.email)
            if client_profil not in participants:
                participants.append(client_profil)
        except:
            pass  # Client n'a pas de Profil
        
        # Ajouter le livreur si assigné
        if instance.livreur:
            participants.append(instance.livreur.profil)
        
        conversation.participants.set(participants)


@receiver(post_save, sender=Livraison)
def ajouter_livreur_conversation(sender, instance, update_fields, **kwargs):
    """Ajoute le livreur à la conversation quand il est assigné."""
    if update_fields and 'livreur' in update_fields and instance.livreur:
        try:
            conversation = instance.conversation
            if instance.livreur.profil not in conversation.participants.all():
                conversation.participants.add(instance.livreur.profil)
        except Conversation.DoesNotExist:
            pass
