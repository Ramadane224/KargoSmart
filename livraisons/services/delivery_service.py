from django.db import transaction
from django.utils import timezone
from ..models import HistoriqueLivraison, Livraison, StatutLivraison


class DeliveryError(Exception):
    pass


ALLOWED_TRANSITIONS = {
    StatutLivraison.EN_ATTENTE:         [StatutLivraison.ASSIGNEE, StatutLivraison.ANNULEE],
    StatutLivraison.ASSIGNEE:           [StatutLivraison.EN_ROUTE, StatutLivraison.ANNULEE],
    StatutLivraison.EN_ROUTE:           [StatutLivraison.EN_COURS, StatutLivraison.ANNULEE],
    StatutLivraison.EN_COURS:           [StatutLivraison.PROCHE_DESTINATION, StatutLivraison.ARRIVEE, StatutLivraison.ANNULEE],
    StatutLivraison.PROCHE_DESTINATION: [StatutLivraison.ARRIVEE, StatutLivraison.LIVREE, StatutLivraison.ANNULEE, StatutLivraison.ECHOUEE],
    StatutLivraison.ARRIVEE:            [StatutLivraison.LIVREE, StatutLivraison.ANNULEE],
    StatutLivraison.LIVREE:             [StatutLivraison.TERMINEE],
    StatutLivraison.TERMINEE:           [],
    StatutLivraison.ANNULEE:            [],
    StatutLivraison.ECHOUEE:            [],
}


def get_allowed_transitions(livraison):
    return ALLOWED_TRANSITIONS.get(livraison.statut, [])


@transaction.atomic
def assign_livreur(livraison, livreur, utilisateur, commentaire=None):
    if livraison.statut not in [StatutLivraison.EN_ATTENTE, StatutLivraison.ASSIGNEE]:
        raise DeliveryError(f'Statut {livraison.statut} incompatible pour assignation')
    ancien = livraison.statut
    livraison.livreur = livreur
    livraison.statut = StatutLivraison.ASSIGNEE
    if not livraison.date_assignation:
        livraison.date_assignation = timezone.now()
    livraison.save(update_fields=['livreur', 'statut', 'date_assignation'])
    HistoriqueLivraison.objects.create(
        livraison=livraison,
        ancien_statut=ancien,
        nouveau_statut=StatutLivraison.ASSIGNEE,
        modifie_par=utilisateur,
        commentaire=commentaire or f'Livreur {livreur.profil.get_full_name() or livreur.profil.username} assigné',
    )
    return livraison


@transaction.atomic
def transition_statut(livraison, nouveau_statut, utilisateur, commentaire=None, force=False):
    if nouveau_statut not in dict(StatutLivraison.choices):
        raise DeliveryError('Statut invalide')
    if not force and nouveau_statut not in get_allowed_transitions(livraison):
        raise DeliveryError(f'Transition {livraison.statut} → {nouveau_statut} non autorisée')

    ancien = livraison.statut
    livraison.statut = nouveau_statut
    fields = ['statut']
    if nouveau_statut == StatutLivraison.ASSIGNEE and not livraison.date_assignation:
        livraison.date_assignation = timezone.now()
        fields.append('date_assignation')
    if nouveau_statut == StatutLivraison.LIVREE and not livraison.date_livraison_reelle:
        livraison.date_livraison_reelle = timezone.now()
        fields.append('date_livraison_reelle')
    if nouveau_statut == StatutLivraison.TERMINEE and not livraison.date_livraison_reelle:
        livraison.date_livraison_reelle = timezone.now()
        fields.append('date_livraison_reelle')
    livraison.save(update_fields=fields)

    HistoriqueLivraison.objects.create(
        livraison=livraison,
        ancien_statut=ancien,
        nouveau_statut=nouveau_statut,
        modifie_par=utilisateur,
        commentaire=commentaire or 'Statut modifié',
    )
    return livraison
