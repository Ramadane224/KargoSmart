from rest_framework.permissions import BasePermission
from django.contrib.auth.mixins import UserPassesTestMixin


# --- Fonctions utilitaires ---
def est_admin(utilisateur):
    return utilisateur.is_authenticated and getattr(utilisateur, 'role', None) == 'ADMINISTRATEUR'


def est_gestionnaire(utilisateur):
    return utilisateur.is_authenticated and getattr(utilisateur, 'role', None) in ['ADMINISTRATEUR', 'GESTIONNAIRE']


def est_livreur(utilisateur):
    return utilisateur.is_authenticated and getattr(utilisateur, 'role', None) == 'LIVREUR'


def est_client(utilisateur):
    return utilisateur.is_authenticated and getattr(utilisateur, 'role', None) == 'CLIENT'


# --- Mixins pour les vues class-based ---
class AdminRequis(UserPassesTestMixin):
    def test_func(self):
        return est_admin(self.request.user)


class GestionnaireRequis(UserPassesTestMixin):
    def test_func(self):
        return est_gestionnaire(self.request.user)


class GestionnaireOuAdminRequis(UserPassesTestMixin):
    def test_func(self):
        return est_gestionnaire(self.request.user)


class LivreurRequis(UserPassesTestMixin):
    def test_func(self):
        return est_livreur(self.request.user)


class ClientRequis(UserPassesTestMixin):
    def test_func(self):
        return est_client(self.request.user)


# Compatibilité noms précédents
AdminRequiredMixin = AdminRequis
GestionnaireRequiredMixin = GestionnaireRequis


# --- Permissions DRF pour les API ---
class EstAdmin(BasePermission):
    message = "Accès réservé aux administrateurs."

    def has_permission(self, request, view):
        return est_admin(request.user)


class EstGestionnaire(BasePermission):
    message = "Accès réservé aux gestionnaires et administrateurs."

    def has_permission(self, request, view):
        return est_gestionnaire(request.user)


class EstLivreur(BasePermission):
    message = "Accès réservé aux livreurs."

    def has_permission(self, request, view):
        return est_livreur(request.user)


class EstClient(BasePermission):
    message = "Accès réservé aux clients."

    def has_permission(self, request, view):
        return est_client(request.user)


class EstProprietaireLivraison(BasePermission):
    """Un livreur ne peut agir que sur SES propres livraisons."""
    message = "Vous ne pouvez agir que sur vos propres livraisons."

    def has_object_permission(self, request, view, obj):
        if est_gestionnaire(request.user):
            return True
        if est_livreur(request.user):
            try:
                return obj.livreur and obj.livreur.profil == request.user
            except Exception:
                return False
        return False


class EstClientOuGestionnaire(BasePermission):
    """Gestion des conversations et accès messagerie."""
    message = "Accès à cette ressource refusé."

    def has_permission(self, request, view):
        return est_gestionnaire(request.user) or est_client(request.user) or est_livreur(request.user)

    def has_object_permission(self, request, view, obj):
        """Pour les conversations: vérifie que l'utilisateur est participant."""
        try:
            if est_gestionnaire(request.user):
                return True
            if hasattr(obj, 'participants'):
                return request.user in obj.participants.all()
            return False
        except Exception:
            return False
