import random

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from notifications.models import Notification
from utilisateurs.models import ProfilLivreur
from .models import HistoriqueLivraison, Livraison, StatutLivraison


@receiver(pre_save, sender=Livraison)
def livraison_pre_save(sender, instance, **kwargs):
    if instance.pk:
        try:
            previous = sender.objects.get(pk=instance.pk)
            instance._previous_statut = previous.statut
        except sender.DoesNotExist:
            instance._previous_statut = None
    else:
        instance._previous_statut = None


@receiver(post_save, sender=Livraison)
def livraison_post_save(sender, instance, created, **kwargs):
    if created:
        if not instance.code_livraison:
            instance.code_livraison = f'KS-{instance.pk:06d}'
            instance.save(update_fields=['code_livraison'])
        HistoriqueLivraison.objects.create(
            livraison=instance,
            ancien_statut='',
            nouveau_statut=instance.statut,
            modifie_par=instance.createur,
            commentaire='Livraison créée',
        )
        return

    previous_statut = getattr(instance, '_previous_statut', None)
    if previous_statut and previous_statut != instance.statut:
        if instance.livreur is not None:
            Notification.objects.create(
                destinataire=instance.livreur.profil,
                livraison=instance,
                type_notif='ASSIGNEE' if instance.statut == StatutLivraison.ASSIGNEE else 'LIVRAISON_EN_COURS' if instance.statut == StatutLivraison.EN_COURS else 'LIVRAISON_TERMINEE' if instance.statut == StatutLivraison.LIVREE else 'LIVRAISON_ANNULEE',
                titre=f'Statut livraison {instance.code_livraison}',
                message=f'Le statut de la livraison est passé de {previous_statut} à {instance.statut}.',
            )

        Notification.objects.create(
            destinataire=instance.createur,
            livraison=instance,
            type_notif='SYSTEME',
            titre=f'Statut modifié pour {instance.code_livraison}',
            message=f'Votre livraison est maintenant {instance.statut}.',
        )
