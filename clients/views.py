from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from utilisateurs.permissions import GestionnaireOuAdminRequis
from .forms import ClientForm
from .models import Client
from livraisons.models import Livraison


class ListeClientsView(LoginRequiredMixin, ListView):
    model = Client
    template_name = 'clients/liste.html'
    context_object_name = 'clients'
    paginate_by = 15

    def dispatch(self, request, *args, **kwargs):
        """Vérifier les permissions selon le rôle."""
        from utilisateurs.permissions import est_gestionnaire, est_livreur, est_client
        
        if est_gestionnaire(request.user):
            # Gestionnaire/Admin voient TOUS les clients
            return super().dispatch(request, *args, **kwargs)
        elif est_livreur(request.user):
            # Livreur voit les clients de ses livraisons
            return super().dispatch(request, *args, **kwargs)
        else:
            # Client n'y a pas accès
            return HttpResponseForbidden('Accès refusé.')

    def get_queryset(self):
        from utilisateurs.permissions import est_gestionnaire, est_livreur
        from utilisateurs.models import Profil, ProfilLivreur

        queryset = Client.objects.filter(est_actif=True)
        query = self.request.GET.get('q')

        # Exclure les clients orphelins si leur profil utilisateur a été supprimé.
        active_emails = list(Profil.objects.values_list('email', flat=True))
        active_telephones = list(Profil.objects.values_list('telephone', flat=True))
        if active_emails or active_telephones:
            queryset = queryset.filter(
                Q(email__in=active_emails) | Q(email__isnull=True) | Q(email__exact='') |
                Q(telephone__in=active_telephones) | Q(telephone__isnull=True) | Q(telephone__exact='')
            )

        if est_gestionnaire(self.request.user):
            # Admin/Gestion voient tous les clients actifs
            pass
        elif est_livreur(self.request.user):
            # Livreur ne voit que les clients de ses livraisons
            try:
                livreur = self.request.user.profil_livreur
                # Récupérer les clients des livraisons du livreur
                clients_ids = Livraison.objects.filter(
                    livreur=livreur
                ).values_list('client_id', flat=True).distinct()
                queryset = queryset.filter(id__in=clients_ids)
            except ProfilLivreur.DoesNotExist:
                queryset = queryset.none()

        if query:
            queryset = queryset.filter(
                Q(nom__icontains=query) | Q(prenom__icontains=query) | Q(telephone__icontains=query)
            )
        return queryset.order_by('-date_creation')


class DetailClientView(LoginRequiredMixin, DetailView):
    model = Client
    template_name = 'clients/detail.html'
    context_object_name = 'client'

    def dispatch(self, request, *args, **kwargs):
        """Vérifier que livreur ne voit que ses clients."""
        from utilisateurs.permissions import est_gestionnaire, est_livreur
        from utilisateurs.models import ProfilLivreur
        
        obj = self.get_object()

        if not obj.est_actif:
            return HttpResponseForbidden('Accès refusé.')
        
        if est_gestionnaire(request.user):
            return super().dispatch(request, *args, **kwargs)
        elif est_livreur(request.user):
            try:
                livreur = request.user.profil_livreur
                # Vérifier que ce client a travaillé avec ce livreur
                has_livraison = Livraison.objects.filter(
                    livreur=livreur, client=obj
                ).exists()
                if not has_livraison:
                    return HttpResponseForbidden('Accès refusé.')
            except ProfilLivreur.DoesNotExist:
                return HttpResponseForbidden('Accès refusé.')
        else:
            return HttpResponseForbidden('Accès refusé.')
        
        return super().dispatch(request, *args, **kwargs)


class CreerClientView(GestionnaireOuAdminRequis, LoginRequiredMixin, CreateView):
    model = Client
    form_class = ClientForm
    template_name = 'clients/creer.html'
    success_url = reverse_lazy('liste_clients')


class ModifierClientView(GestionnaireOuAdminRequis, LoginRequiredMixin, UpdateView):
    model = Client
    form_class = ClientForm
    template_name = 'clients/modifier.html'
    success_url = reverse_lazy('liste_clients')
