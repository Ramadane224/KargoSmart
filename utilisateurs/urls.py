from django.urls import path

from .views import (
    ActivationLivreur,
    ConnexionView,
    CreerUtilisateurView,
    DeconnexionView,
    InscriptionView,
    ListeUtilisateurs,
    ModifierUtilisateurView,
    ProfilView,
    SupprimerUtilisateurView,
)

urlpatterns = [
    path('connexion/', ConnexionView.as_view(), name='connexion'),
    path('deconnexion/', DeconnexionView.as_view(), name='deconnexion'),
    path('inscription/', InscriptionView.as_view(), name='inscription'),
    path('profil/', ProfilView.as_view(), name='profil'),
    path('profil/<int:pk>/', ProfilView.as_view(), name='profil_detail'),
    path('liste/', ListeUtilisateurs.as_view(), name='liste_utilisateurs'),
    path('creer/', CreerUtilisateurView.as_view(), name='creer_utilisateur'),
    path('<int:pk>/modifier/', ModifierUtilisateurView.as_view(), name='modifier_utilisateur'),
    path('<int:pk>/supprimer/', SupprimerUtilisateurView.as_view(), name='supprimer_utilisateur'),
    path('livreurs/<int:pk>/activer/', ActivationLivreur.as_view(), name='activer_livreur'),
]
