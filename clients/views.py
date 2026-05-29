from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from utilisateurs.permissions import GestionnaireOuAdminRequis
from .forms import ClientForm
from .models import Client


class ListeClientsView(GestionnaireOuAdminRequis, LoginRequiredMixin, ListView):
    model = Client
    template_name = 'clients/liste.html'
    context_object_name = 'clients'
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset().filter(est_actif=True)
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(nom__icontains=query) | Q(prenom__icontains=query) | Q(telephone__icontains=query)
            )
        return queryset.order_by('-date_creation')


class DetailClientView(GestionnaireOuAdminRequis, LoginRequiredMixin, DetailView):
    model = Client
    template_name = 'clients/detail.html'
    context_object_name = 'client'


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
