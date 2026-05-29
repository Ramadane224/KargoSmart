import uuid

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView, View
from utilisateurs.permissions import AdminRequiredMixin

from notifications.models import Notification
from utilisateurs.models import ProfilLivreur
from .forms import LivraisonForm
from .models import HistoriqueLivraison, Livraison, PaiementMobile, PositionLivreur, StatutLivraison, haversine_km

VITESSE_MOYENNE_KMH = 25

TRANSITIONS_VALIDES = {
    StatutLivraison.EN_ATTENTE:         [StatutLivraison.ASSIGNEE, StatutLivraison.EN_ROUTE, StatutLivraison.ANNULEE],
    StatutLivraison.ASSIGNEE:           [StatutLivraison.EN_ROUTE, StatutLivraison.ANNULEE],
    StatutLivraison.EN_ROUTE:           [StatutLivraison.EN_COURS, StatutLivraison.ANNULEE],
    StatutLivraison.EN_COURS:           [StatutLivraison.PROCHE_DESTINATION, StatutLivraison.LIVREE, StatutLivraison.ECHOUEE],
    StatutLivraison.PROCHE_DESTINATION: [StatutLivraison.LIVREE, StatutLivraison.ECHOUEE],
    StatutLivraison.LIVREE:             [],
    StatutLivraison.ANNULEE:            [],
    StatutLivraison.ECHOUEE:            [],
}


class ListeLivraisonsView(LoginRequiredMixin, ListView):
    model = Livraison
    template_name = 'livraisons/liste.html'
    context_object_name = 'livraisons'
    paginate_by = 15

    def get_queryset(self):
        from utilisateurs.permissions import est_gestionnaire, est_livreur, est_client
        
        qs = super().get_queryset().select_related('client', 'livreur__profil')
        
        # Filtrer selon le rôle
        if est_gestionnaire(self.request.user):
            pass  # Les gestionnaires/admins voient TOUT
        elif est_livreur(self.request.user):
            # Les livreurs ne voient que leurs livraisons assignées
            try:
                livreur_profile = self.request.user.profil_livreur
                qs = qs.filter(livreur=livreur_profile)
            except:
                qs = qs.none()
        elif est_client(self.request.user):
            # Les clients ne voient que leurs livraisons
            try:
                from clients.models import Client
                client = Client.objects.get(email=self.request.user.email) or Client.objects.filter(telephone=self.request.user.telephone).first()
                if client:
                    qs = qs.filter(client=client)
                else:
                    qs = qs.none()
            except:
                qs = qs.none()
        else:
            qs = qs.none()
        
        if s := self.request.GET.get('statut'):
            qs = qs.filter(statut=s)
        if q := self.request.GET.get('q'):
            qs = qs.filter(code_livraison__icontains=q)
        return qs.order_by('-date_creation')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['statuts'] = StatutLivraison.choices
        ctx['statut_actif'] = self.request.GET.get('statut', '')
        return ctx


class DetailLivraisonView(LoginRequiredMixin, DetailView):
    model = Livraison
    template_name = 'livraisons/detail.html'
    context_object_name = 'livraison'

    def dispatch(self, request, *args, **kwargs):
        from utilisateurs.permissions import est_gestionnaire, est_livreur, est_client
        obj = self.get_object()
        
        if est_gestionnaire(request.user):
            return super().dispatch(request, *args, **kwargs)
        elif est_livreur(request.user):
            try:
                if obj.livreur.profil != request.user:
                    return HttpResponseForbidden('Vous ne pouvez voir que vos propres livraisons.')
            except:
                return HttpResponseForbidden('Accès refusé.')
        elif est_client(request.user):
            try:
                from clients.models import Client
                client = Client.objects.filter(email=request.user.email).first() or Client.objects.filter(telephone=request.user.telephone).first()
                if not client or obj.client != client:
                    return HttpResponseForbidden('Vous ne pouvez voir que vos propres livraisons.')
            except:
                return HttpResponseForbidden('Accès refusé.')
        else:
            return HttpResponseForbidden('Accès refusé.')
        
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['historique'] = self.object.historique.order_by('-date_changement')
        ctx['livreurs_disponibles'] = ProfilLivreur.objects.filter(est_actif=True).select_related('profil')
        transitions = TRANSITIONS_VALIDES.get(self.object.statut, [])
        ctx['transitions_valides'] = [(v, l) for v, l in StatutLivraison.choices if v in transitions]
        ctx['position_livreur'] = None
        if self.object.livreur:
            try:
                ctx['position_livreur'] = self.object.livreur.position_gps
            except PositionLivreur.DoesNotExist:
                pass
        return ctx


class CreerLivraisonView(LoginRequiredMixin, CreateView):
    model = Livraison
    form_class = LivraisonForm
    template_name = 'livraisons/creer.html'
    success_url = reverse_lazy('liste_livraisons')

    def dispatch(self, request, *args, **kwargs):
        if request.user.role not in ['ADMINISTRATEUR', 'GESTIONNAIRE']:
            return HttpResponseForbidden('Accès réservé aux administrateurs et gestionnaires pour créer une livraison.')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        livraison = form.save(commit=False)
        livraison.createur = self.request.user
        livraison.code_livraison = self._code_unique()
        if all([livraison.latitude_depart, livraison.longitude_depart,
                livraison.latitude_arrivee, livraison.longitude_arrivee]):
            dist = haversine_km(livraison.latitude_depart, livraison.longitude_depart,
                                livraison.latitude_arrivee, livraison.longitude_arrivee)
            livraison.distance_km = round(dist, 2)
            livraison.duree_estimee_min = int((dist / VITESSE_MOYENNE_KMH) * 60)
        livraison.save()  # save direct — pas de double save
        return self._redirect()

    def _redirect(self):
        from django.shortcuts import redirect
        return redirect(self.success_url)

    def _code_unique(self):
        while True:
            code = f'KS-{uuid.uuid4().hex[:6].upper()}'
            if not Livraison.objects.filter(code_livraison=code).exists():
                return code


class ModifierLivraisonView(LoginRequiredMixin, UpdateView):
    model = Livraison
    form_class = LivraisonForm
    template_name = 'livraisons/modifier.html'
    success_url = reverse_lazy('liste_livraisons')

    def dispatch(self, request, *args, **kwargs):
        if request.user.role not in ['ADMINISTRATEUR', 'GESTIONNAIRE']:
            return HttpResponseForbidden('Accès réservé aux administrateurs et gestionnaires pour modifier une livraison.')
        return super().dispatch(request, *args, **kwargs)


class SupprimerLivraisonView(AdminRequiredMixin, LoginRequiredMixin, DeleteView):
    model = Livraison
    template_name = 'livraisons/confirmer_suppression.html'
    success_url = reverse_lazy('liste_livraisons')
    raise_exception = True

    def dispatch(self, request, *args, **kwargs):
        if request.user.role in ['LIVREUR', 'CLIENT']:
            return HttpResponseForbidden('Accès refusé aux livreurs et clients pour la suppression de livraison.')
        return super().dispatch(request, *args, **kwargs)


class AssignerLivreurView(LoginRequiredMixin, View):
    def post(self, request, pk):
        livraison = get_object_or_404(Livraison, pk=pk)
        livreur_id = request.POST.get('livreur_id')
        if not livreur_id:
            return JsonResponse({'success': False, 'error': 'livreur_id manquant'}, status=400)
        if livraison.statut not in [StatutLivraison.EN_ATTENTE, StatutLivraison.ASSIGNEE]:
            return JsonResponse({'success': False, 'error': f'Statut {livraison.statut} incompatible'}, status=400)
        livreur = get_object_or_404(ProfilLivreur, pk=livreur_id, est_actif=True)
        ancien = livraison.statut
        livraison.livreur = livreur
        livraison.statut = StatutLivraison.ASSIGNEE
        livraison.save()
        HistoriqueLivraison.objects.create(
            livraison=livraison, ancien_statut=ancien,
            nouveau_statut=StatutLivraison.ASSIGNEE, modifie_par=request.user,
            commentaire=f'Livreur {livreur.profil.get_full_name() or livreur.profil.username} assigné',
        )
        Notification.objects.create(
            destinataire=livreur.profil, livraison=livraison,
            type_notif='ASSIGNEE', titre='Livraison assignée',
            message=f'La livraison {livraison.code_livraison} vous a été assignée.',
        )
        return JsonResponse({'success': True})


class ChangerStatutView(LoginRequiredMixin, View):
    def post(self, request, pk):
        livraison = get_object_or_404(Livraison, pk=pk)
        nouveau = request.POST.get('nouveau_statut', '').strip()
        if not nouveau or nouveau not in dict(StatutLivraison.choices):
            return JsonResponse({'success': False, 'error': 'Statut invalide'}, status=400)
        if nouveau not in TRANSITIONS_VALIDES.get(livraison.statut, []):
            return JsonResponse({'success': False, 'error': f'{livraison.statut}→{nouveau} non autorisé'}, status=400)
        ancien = livraison.statut
        livraison.statut = nouveau
        livraison.save()
        HistoriqueLivraison.objects.create(
            livraison=livraison, ancien_statut=ancien, nouveau_statut=nouveau,
            modifie_par=request.user,
            commentaire=request.POST.get('commentaire', 'Statut modifié'),
        )
        return JsonResponse({'success': True, 'statut': nouveau})


class AnnulerLivraisonView(LoginRequiredMixin, View):
    def post(self, request, pk):
        livraison = get_object_or_404(Livraison, pk=pk)
        if livraison.statut not in [StatutLivraison.EN_ATTENTE, StatutLivraison.ASSIGNEE]:
            return HttpResponseForbidden('Impossible d\'annuler à ce stade')
        ancien = livraison.statut
        livraison.statut = StatutLivraison.ANNULEE
        livraison.save()
        HistoriqueLivraison.objects.create(
            livraison=livraison, ancien_statut=ancien,
            nouveau_statut=StatutLivraison.ANNULEE, modifie_par=request.user,
            commentaire='Annulation',
        )
        return JsonResponse({'success': True})


class PaiementMobileView(LoginRequiredMixin, View):
    def get(self, request, pk):
        livraison = get_object_or_404(Livraison, pk=pk)
        try:
            p = livraison.paiement
            return JsonResponse({'statut': p.statut, 'reference': p.reference, 'operateur': p.operateur})
        except PaiementMobile.DoesNotExist:
            return JsonResponse({'statut': None})

    def post(self, request, pk):
        livraison = get_object_or_404(Livraison, pk=pk)
        operateur = request.POST.get('operateur', '')
        numero = request.POST.get('numero_telephone', '').strip()
        if operateur not in ('ORANGE', 'MTN'):
            return HttpResponseBadRequest('Opérateur invalide')
        if not numero:
            return HttpResponseBadRequest('Numéro requis')
        try:
            reference = livraison.paiement.reference
        except PaiementMobile.DoesNotExist:
            reference = f'KS{uuid.uuid4().hex[:8].upper()}'
        paiement, _ = PaiementMobile.objects.update_or_create(
            livraison=livraison,
            defaults={'operateur': operateur, 'numero_telephone': numero,
                      'montant': livraison.cout_estime, 'reference': reference, 'statut': 'EN_ATTENTE'},
        )
        return JsonResponse({'success': True, 'reference': paiement.reference,
                             'message': f'Demande envoyée au {numero}. Confirmez sur votre téléphone.'})


class ConfirmerPaiementView(LoginRequiredMixin, View):
    def post(self, request, pk):
        livraison = get_object_or_404(Livraison, pk=pk)
        try:
            paiement = livraison.paiement
        except PaiementMobile.DoesNotExist:
            return HttpResponseBadRequest('Aucun paiement initié')
        if request.POST.get('action') == 'confirmer':
            paiement.statut = 'CONFIRME'
            paiement.date_confirmation = timezone.now()
            livraison.est_paye = True
            livraison.save(update_fields=['est_paye'])
        else:
            paiement.statut = 'ECHOUE'
        paiement.save()
        return JsonResponse({'success': True, 'statut': paiement.statut})
