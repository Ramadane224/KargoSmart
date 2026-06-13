from django.db.models import Q
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Profil


@receiver(post_delete, sender=Profil)
def desactiver_client_lie(sender, instance, **kwargs):
    """
    Quand un profil client est supprimé depuis l'admin, désactive les enregistrements
    Client correspondants pour ne plus les afficher dans la liste.
    """
    if instance.role != 'CLIENT':
        return

    if not instance.email and not instance.telephone:
        return

    from clients.models import Client

    conditions = Q()
    if instance.email:
        conditions |= Q(email__iexact=instance.email)
    if instance.telephone:
        conditions |= Q(telephone__iexact=instance.telephone)

    if conditions:
        Client.objects.filter(conditions).update(est_actif=False)
