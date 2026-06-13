import json

from django.test import TestCase, override_settings

from clients.models import Client
from utilisateurs.models import Profil, ProfilLivreur
from .models import Livraison, PaiementMobile, StatutLivraison
from .services.delivery_service import (
    assign_livreur,
    get_allowed_transitions,
    transition_statut,
    DeliveryError,
)
from .services.payment_service import PaymentService, PaymentError


class LivraisonWorkflowTests(TestCase):
    def setUp(self):
        self.admin = Profil.objects.create_user(
            username='admin', password='adminpass', telephone='0000000000', role='ADMINISTRATEUR', email='admin@example.com'
        )
        self.client_entity = Client.objects.create(
            nom='Doe', prenom='John', telephone='221000000', email='john@example.com', adresse='Conakry'
        )
        self.livraison = Livraison.objects.create(
            code_livraison='KS-TEST01',
            client=self.client_entity,
            createur=self.admin,
            adresse_depart='Point A',
            adresse_arrivee='Point B',
            description_colis='Documents',
            poids_estime_kg=1.5,
            cout_estime=5000,
            mode_paiement='ORANGE',
            statut=StatutLivraison.EN_ATTENTE,
        )
        self.deliver_user = Profil.objects.create_user(
            username='livreur', password='livreurpass', telephone='221111111', role='LIVREUR', email='livreur@example.com'
        )
        self.livreur = ProfilLivreur.objects.create(
            profil=self.deliver_user,
            type_vehicule='MOTO', est_actif=True, est_disponible=True,
        )

    def test_allowed_transitions_follow_workflow(self):
        self.assertEqual(get_allowed_transitions(self.livraison), [StatutLivraison.ASSIGNEE, StatutLivraison.ANNULEE])
        assign_livreur(self.livraison, self.livreur, self.admin)
        self.livraison.refresh_from_db()
        self.assertEqual(self.livraison.statut, StatutLivraison.ASSIGNEE)
        self.assertIsNotNone(self.livraison.date_assignation)

        transition_statut(self.livraison, StatutLivraison.EN_ROUTE, self.admin)
        self.livraison.refresh_from_db()
        self.assertEqual(self.livraison.statut, StatutLivraison.EN_ROUTE)

        transition_statut(self.livraison, StatutLivraison.EN_COURS, self.admin)
        transition_statut(self.livraison, StatutLivraison.ARRIVEE, self.admin)
        transition_statut(self.livraison, StatutLivraison.LIVREE, self.admin)
        transition_statut(self.livraison, StatutLivraison.TERMINEE, self.admin)
        self.livraison.refresh_from_db()
        self.assertEqual(self.livraison.statut, StatutLivraison.TERMINEE)
        self.assertTrue(self.livraison.date_livraison_reelle)

    def test_invalid_transition_raises(self):
        with self.assertRaises(DeliveryError):
            transition_statut(self.livraison, StatutLivraison.LIVREE, self.admin)

    def test_cancel_from_assignee_allowed(self):
        assign_livreur(self.livraison, self.livreur, self.admin)
        self.livraison.refresh_from_db()
        transition_statut(self.livraison, StatutLivraison.ANNULEE, self.admin)
        self.livraison.refresh_from_db()
        self.assertEqual(self.livraison.statut, StatutLivraison.ANNULEE)


class PaymentServiceTests(TestCase):
    def setUp(self):
        self.admin = Profil.objects.create_user(
            username='admin2', password='adminpass', telephone='0000000001', role='ADMINISTRATEUR', email='admin2@example.com'
        )
        self.client_entity = Client.objects.create(
            nom='Doe', prenom='Jane', telephone='221000001', email='jane@example.com', adresse='Ratoma'
        )
        self.livraison = Livraison.objects.create(
            code_livraison='KS-TEST02',
            client=self.client_entity,
            createur=self.admin,
            adresse_depart='Bureau',
            adresse_arrivee='Maison',
            description_colis='Colis léger',
            poids_estime_kg=2.0,
            cout_estime=8000,
            mode_paiement='ORANGE',
            statut=StatutLivraison.EN_ATTENTE,
        )

    @override_settings(DEBUG=True)
    def test_initiate_payment_simulation_sets_success_and_marks_livraison(self):
        paiement = PaymentService.initiate_payment(self.livraison, 'ORANGE', '221123456')
        self.livraison.refresh_from_db()
        self.assertEqual(paiement.statut, PaiementMobile.STATUT_SUCCESS)
        self.assertIsNotNone(paiement.transaction_id)
        self.assertTrue(self.livraison.est_paye)

    @override_settings(DEBUG=True)
    def test_confirm_payment_is_idempotent(self):
        paiement = PaymentService.initiate_payment(self.livraison, 'ORANGE', '221123456')
        paiement_confirmed = PaymentService.confirm_payment(reference=paiement.reference)
        self.assertEqual(paiement_confirmed.statut, PaiementMobile.STATUT_SUCCESS)
        self.assertEqual(paiement_confirmed.pk, paiement.pk)

    @override_settings(DEBUG=True)
    def test_fail_payment_sets_failed(self):
        from .models import PaiementMobile

        paiement = PaiementMobile.objects.create(
            livraison=self.livraison,
            operateur='ORANGE',
            numero_telephone='221123456',
            montant=self.livraison.cout_estime,
            reference='KSTESTFAIL001',
            statut=PaiementMobile.STATUT_PENDING,
        )
        failed = PaymentService.fail_payment(reference=paiement.reference)
        self.assertEqual(failed.statut, PaiementMobile.STATUT_FAILED)

    def test_initiate_payment_invalid_operator_raises(self):
        with self.assertRaises(PaymentError):
            PaymentService.initiate_payment(self.livraison, 'INVALID', '221123456')

    @override_settings(PAYMENT_CALLBACK_SECRET='secret-callback-token')
    def test_callback_endpoint_confirms_payment_with_valid_token(self):
        from django.urls import reverse
        from .models import PaiementMobile

        paiement = PaiementMobile.objects.create(
            livraison=self.livraison,
            operateur='ORANGE',
            numero_telephone='221123456',
            montant=self.livraison.cout_estime,
            reference='KSREF123',
            statut=PaiementMobile.STATUT_PENDING,
        )
        url = reverse('paiement_callback')
        response = self.client.post(
            url,
            data=json.dumps({
                'reference': paiement.reference,
                'status': 'SUCCESS',
            }),
            HTTP_X_PAYMENT_CALLBACK_TOKEN='secret-callback-token',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['success'], True)
        paiement.refresh_from_db()
        self.assertEqual(paiement.statut, PaiementMobile.STATUT_SUCCESS)

    @override_settings(PAYMENT_CALLBACK_SECRET='secret-callback-token')
    def test_callback_endpoint_rejects_invalid_token(self):
        from django.urls import reverse
        from .models import PaiementMobile

        paiement = PaiementMobile.objects.create(
            livraison=self.livraison,
            operateur='MTN',
            numero_telephone='221123456',
            montant=self.livraison.cout_estime,
            reference='KSREF124',
            statut=PaiementMobile.STATUT_PENDING,
        )
        url = reverse('paiement_callback')
        response = self.client.post(
            url,
            data=json.dumps({'reference': paiement.reference, 'status': 'SUCCESS'}),
            HTTP_X_PAYMENT_CALLBACK_TOKEN='wrong-token',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)
        paiement.refresh_from_db()
        self.assertEqual(paiement.statut, PaiementMobile.STATUT_PENDING)

    @override_settings(PAYMENT_CALLBACK_SECRET='secret-callback-token')
    def test_callback_endpoint_fails_payment_status(self):
        from django.urls import reverse
        from .models import PaiementMobile

        paiement = PaiementMobile.objects.create(
            livraison=self.livraison,
            operateur='MTN',
            numero_telephone='221123456',
            montant=self.livraison.cout_estime,
            reference='KSREF125',
            statut=PaiementMobile.STATUT_PENDING,
        )
        url = reverse('paiement_callback')
        response = self.client.post(
            url,
            data=json.dumps({'reference': paiement.reference, 'status': 'FAILED'}),
            HTTP_X_PAYMENT_CALLBACK_TOKEN='secret-callback-token',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['success'], True)
        paiement.refresh_from_db()
        self.assertEqual(paiement.statut, PaiementMobile.STATUT_FAILED)
