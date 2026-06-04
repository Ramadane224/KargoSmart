from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import redirect
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
            from django.contrib import messages
            messages.error(request, '⚠️ Accès refusé. Vous ne pouvez pas consulter la liste des clients.')
            return redirect('tableau_de_bord')

    def get_queryset(self):
        from utilisateurs.permissions import est_gestionnaire, est_livreur
        from utilisateurs.models import ProfilLivreur
        
        queryset = Client.objects.filter(est_actif=True)
        query = self.request.GET.get('q')
        
        if est_gestionnaire(self.request.user):
            # Admin/Gestion voient tous les clients
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
                    from django.contrib import messages
                    messages.error(request, '⚠️ Accès refusé. Vous n\'avez pas accès à ce client.')
                    return redirect('liste_clients')
            except ProfilLivreur.DoesNotExist:
                from django.contrib import messages
                messages.error(request, '⚠️ Accès refusé.')
                return redirect('tableau_de_bord')
        else:
            from django.contrib import messages
            messages.error(request, '⚠️ Accès refusé.')
            return redirect('tableau_de_bord')
        
        return super().dispatch(request, *args, **kwargs)


class CreerClientView(GestionnaireOuAdminRequis, LoginRequiredMixin, CreateView):
    model = Client
    form_class = ClientForm
    template_name = 'clients/creer.html'
    success_url = reverse_lazy('liste_clients')


class ModifierClientView(GestionnaireOuAdminRequis, LoginRequiredMixin, UpdateView):
    model = Client
    fields = ['nom', 'prenom', 'telephone', 'email', 'adresse', 'quartier', 'commune', 'notes_internes', 'est_actif']
    template_name = 'clients/modifier.html'
    success_url = reverse_lazy('liste_clients')
