from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView, View

from .forms import AdminUserForm, ConnexionForm, InscriptionForm
from .models import Profil, ProfilLivreur, Role
from .permissions import AdminRequis


class ConnexionView(LoginView):
    template_name = 'utilisateurs/connexion.html'
    authentication_form = ConnexionForm


class DeconnexionView(View):
    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect('connexion')

    def post(self, request, *args, **kwargs):
        logout(request)
        return redirect('connexion')


class InscriptionView(CreateView):
    model = get_user_model()
    form_class = InscriptionForm
    template_name = 'utilisateurs/inscription.html'
    success_url = reverse_lazy('connexion')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Compte créé avec succès.')
        return response


class ProfilView(LoginRequiredMixin, DetailView):
    model = get_user_model()
    template_name = 'utilisateurs/profil.html'

    def get_object(self, queryset=None):
        if self.kwargs.get('pk'):
            return super().get_object(queryset)
        return self.request.user


class _AdminMixin(AdminRequis):
    pass


class ListeUtilisateurs(_AdminMixin, ListView):
    model = get_user_model()
    template_name = 'utilisateurs/liste_utilisateurs.html'
    context_object_name = 'utilisateurs'
    ordering = ['username']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['livreurs'] = ProfilLivreur.objects.select_related('profil').all()
        return context


class CreerUtilisateurView(_AdminMixin, CreateView):
    model = get_user_model()
    form_class = AdminUserForm
    template_name = 'utilisateurs/form_utilisateur.html'
    success_url = reverse_lazy('liste_utilisateurs')

    def form_valid(self, form):
        messages.success(self.request, 'Utilisateur créé.')
        return super().form_valid(form)


class ModifierUtilisateurView(_AdminMixin, UpdateView):
    model = get_user_model()
    form_class = AdminUserForm
    template_name = 'utilisateurs/form_utilisateur.html'
    success_url = reverse_lazy('liste_utilisateurs')

    def form_valid(self, form):
        messages.success(self.request, 'Utilisateur mis à jour.')
        return super().form_valid(form)


class SupprimerUtilisateurView(_AdminMixin, DeleteView):
    model = get_user_model()
    template_name = 'utilisateurs/confirmer_suppression.html'
    success_url = reverse_lazy('liste_utilisateurs')

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj == self.request.user:
            raise PermissionDenied('Impossible de supprimer votre propre compte.')
        return obj

    def form_valid(self, form):
        messages.success(self.request, 'Utilisateur supprimé.')
        return super().form_valid(form)


class ActivationLivreur(_AdminMixin, View):
    def post(self, request, pk, *args, **kwargs):
        profil_livreur = get_object_or_404(ProfilLivreur, pk=pk)
        profil_livreur.est_actif = not profil_livreur.est_actif
        profil_livreur.save()
        etat = 'activé' if profil_livreur.est_actif else 'désactivé'
        messages.success(request, f'Livreur {etat}.')
        return redirect('liste_utilisateurs')
