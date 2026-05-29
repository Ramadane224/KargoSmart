from django.urls import path

from .views import (
    AnnulerLivraisonView,
    AssignerLivreurView,
    ChangerStatutView,
    ConfirmerPaiementView,
    CreerLivraisonView,
    DetailLivraisonView,
    ListeLivraisonsView,
    ModifierLivraisonView,
    PaiementMobileView,
    SupprimerLivraisonView,
)

urlpatterns = [
    path('', ListeLivraisonsView.as_view(), name='liste_livraisons'),
    path('creer/', CreerLivraisonView.as_view(), name='creer_livraison'),
    path('<int:pk>/', DetailLivraisonView.as_view(), name='detail_livraison'),
    path('<int:pk>/modifier/', ModifierLivraisonView.as_view(), name='modifier_livraison'),
    path('<int:pk>/supprimer/', SupprimerLivraisonView.as_view(), name='supprimer_livraison'),
    path('<int:pk>/assigner/', AssignerLivreurView.as_view(), name='assigner_livreur'),
    path('<int:pk>/statut/', ChangerStatutView.as_view(), name='changer_statut'),
    path('<int:pk>/annuler/', AnnulerLivraisonView.as_view(), name='annuler_livraison'),
    path('<int:pk>/paiement/', PaiementMobileView.as_view(), name='paiement_mobile'),
    path('<int:pk>/paiement/confirmer/', ConfirmerPaiementView.as_view(), name='confirmer_paiement'),
]
