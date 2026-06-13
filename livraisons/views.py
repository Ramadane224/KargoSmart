import json
import uuid

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView, View
from utilisateurs.permissions import AdminRequiredMixin

from notifications.models import Notification
from utilisateurs.models import ProfilLivreur
from .forms import LivraisonForm
from .models import HistoriqueLivraison, Livraison, PaiementMobile, PositionLivreur, StatutLivraison, haversine_km
from .services.delivery_service import (
    assign_livreur,
    get_allowed_transitions,
    transition_statut,
    DeliveryError,
)
from .services.payment_service import PaymentService, PaymentError

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

TOUS_STATUTS_ACTIFS = [
    StatutLivraison.ASSIGNEE, StatutLivraison.EN_ROUTE,
    StatutLivraison.EN_COURS, StatutLivraison.PROCHE_DESTINATION,
    StatutLivraison.LIVREE, StatutLivraison.ANNULEE, StatutLivraison.ECHOUEE,
]


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
            except Exception:
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
            except Exception:
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
            except Exception:
                return HttpResponseForbidden('Accès refusé.')
        elif est_client(request.user):
            try:
                from clients.models import Client
                client = Client.objects.filter(email=request.user.email).first() or Client.objects.filter(telephone=request.user.telephone).first()
                if not client or obj.client != client:
                    return HttpResponseForbidden('Vous ne pouvez voir que vos propres livraisons.')
            except Exception:
                return HttpResponseForbidden('Accès refusé.')
        else:
            return HttpResponseForbidden('Accès refusé.')
        
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['historique'] = self.object.historique.order_by('-date_changement')
        ctx['livreurs_disponibles'] = ProfilLivreur.objects.filter(
            est_actif=True, est_disponible=True
        ).select_related('profil')

        transitions = get_allowed_transitions(self.object)
        ctx['transitions_valides'] = [(v, l) for v, l in StatutLivraison.choices if v in transitions]
        ctx['is_admin'] = self.request.user.role == 'ADMINISTRATEUR'
        ctx['position_livreur'] = None
        if self.object.livreur:
            try:
                pos = self.object.livreur.position_gps
                if pos.livraison_en_cours_id == self.object.pk:
                    ctx['position_livreur'] = pos
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
            from django.contrib import messages
            messages.error(request, '⚠️ Accès réservé aux administrateurs et gestionnaires pour créer une livraison.')
            return redirect('liste_livraisons')
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
    def dispatch(self, request, *args, **kwargs):
        if request.user.role not in ['ADMINISTRATEUR', 'GESTIONNAIRE']:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Accès refusé'}, status=403)
            return HttpResponseForbidden('Accès réservé aux administrateurs et gestionnaires pour assigner un livreur.')
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk):
        livraison = get_object_or_404(Livraison, pk=pk)
        livreur_id = request.POST.get('livreur_id')
        if not livreur_id:
            return JsonResponse({'success': False, 'error': 'livreur_id manquant'}, status=400)
        if livraison.statut not in [StatutLivraison.EN_ATTENTE, StatutLivraison.ASSIGNEE]:
            return JsonResponse({'success': False, 'error': f'Statut {livraison.statut} incompatible'}, status=400)
        livreur = get_object_or_404(ProfilLivreur, pk=livreur_id, est_actif=True, est_disponible=True)
        try:
            livraison = assign_livreur(livraison, livreur, request.user)
        except DeliveryError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

        Notification.objects.create(
            destinataire=livreur.profil, livraison=livraison,
            type_notif='ASSIGNEE', titre='Livraison assignée',
            message=f'La livraison {livraison.code_livraison} vous a été assignée.',
        )
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        return redirect('detail_livraison', pk=pk)


class ChangerStatutView(LoginRequiredMixin, View):
    def post(self, request, pk):
        livraison = get_object_or_404(Livraison, pk=pk)
        nouveau = request.POST.get('nouveau_statut', '').strip()
        if not nouveau or nouveau not in dict(StatutLivraison.choices):
            return JsonResponse({'success': False, 'error': 'Statut invalide'}, status=400)
        try:
            livraison = transition_statut(
                livraison,
                nouveau,
                request.user,
                commentaire=request.POST.get('commentaire', 'Statut modifié'),
            )
            return JsonResponse({'success': True, 'statut': livraison.statut})
        except DeliveryError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


class AnnulerLivraisonView(LoginRequiredMixin, View):
    def post(self, request, pk):
        livraison = get_object_or_404(Livraison, pk=pk)
        try:
            transition_statut(
                livraison,
                StatutLivraison.ANNULEE,
                request.user,
                commentaire='Annulation',
            )
            return JsonResponse({'success': True})
        except DeliveryError as e:
            return HttpResponseForbidden(str(e))


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
            return JsonResponse({'success': False, 'error': 'Opérateur invalide (ORANGE ou MTN)'}, status=400)
        if not numero:
            return JsonResponse({'success': False, 'error': 'Numéro de téléphone requis'}, status=400)
        try:
            paiement = PaymentService.initiate_payment(livraison, operateur, numero)
            return JsonResponse({'success': True, 'reference': paiement.reference,
                                 'message': f'Demande envoyée au {numero}. Vérifiez votre téléphone.'})
        except PaymentError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


class ConfirmerPaiementView(LoginRequiredMixin, View):
    def post(self, request, pk):
        livraison = get_object_or_404(Livraison, pk=pk)
        action = request.POST.get('action')
        try:
            if action == 'confirmer':
                paiement = PaymentService.confirm_payment(reference=request.POST.get('reference'))
                return JsonResponse({'success': True, 'statut': paiement.statut})
            else:
                paiement = PaymentService.fail_payment(reference=request.POST.get('reference'))
                return JsonResponse({'success': True, 'statut': paiement.statut})
        except PaymentError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class PaymentCallbackView(View):
    def post(self, request):
        token = request.headers.get('X-Payment-Callback-Token', '')
        if not token or token != settings.PAYMENT_CALLBACK_SECRET:
            return HttpResponseForbidden('Token de callback invalide')

        payload = {}
        if request.content_type.startswith('application/json'):
            try:
                payload = json.loads(request.body.decode('utf-8') or '{}')
            except json.JSONDecodeError:
                return JsonResponse({'success': False, 'error': 'JSON invalide'}, status=400)
        else:
            payload = request.POST

        reference = payload.get('reference')
        transaction_id = payload.get('transaction_id')
        statut = (payload.get('status') or payload.get('statut') or '').strip().upper()

        if not reference and not transaction_id:
            return JsonResponse({'success': False, 'error': 'reference ou transaction_id requis'}, status=400)
        if statut not in ['SUCCESS', 'FAILED', 'FAILURE', 'CANCELLED', 'REFUNDED']:
            return JsonResponse({'success': False, 'error': 'statut callback inconnu'}, status=400)

        try:
            if statut == 'SUCCESS':
                paiement = PaymentService.confirm_payment(reference=reference, transaction_id=transaction_id)
            elif statut == 'FAILED' or statut == 'FAILURE':
                paiement = PaymentService.fail_payment(reference=reference, transaction_id=transaction_id)
            elif statut == 'CANCELLED':
                paiement = PaymentService.update_status(
                    reference=reference,
                    transaction_id=transaction_id,
                    statut=PaiementMobile.STATUT_CANCELLED,
                )
            else:
                paiement = PaymentService.update_status(
                    reference=reference,
                    transaction_id=transaction_id,
                    statut=PaiementMobile.STATUT_REFUNDED,
                )
            return JsonResponse({'success': True, 'reference': paiement.reference, 'statut': paiement.statut})
        except PaymentError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
