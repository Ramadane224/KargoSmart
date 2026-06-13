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
        except Exception:
            pass  # Client n'a pas de Profil
        
        # Ajouter le livreur si assigné
        if instance.livreur:
            participants.append(instance.livreur.profil)
        
        conversation.participants.set(participants)


@receiver(post_save, sender=Livraison)
def ajouter_livreur_conversation(sender, instance, created, **kwargs):
    """
    Ajoute le livreur à la conversation quand il est assigné.
    FIX : utilise _previous_livreur au lieu de update_fields (toujours None).
    """
    if created:
        return
    previous_livreur = getattr(instance, '_previous_livreur', None)
    if not instance.livreur or instance.livreur == previous_livreur:
        return
    try:
        conversation = instance.conversation
        if instance.livreur.profil not in conversation.participants.all():
            conversation.participants.add(instance.livreur.profil)
    except Conversation.DoesNotExist:
        pass
