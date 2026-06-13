from django.conf import settings
from django.db import transaction
from django.utils import timezone
from ..models import PaiementMobile
import uuid
import logging

logger = logging.getLogger(__name__)

class PaymentError(Exception):
    pass

class PaymentService:
    """Service centralisé pour les paiements mobile (Orange/Mtn).

    Utilisation:
      - En mode DEBUG: simulation locale
      - En production: appeler l'API opérateur (placeholder)
    """

    @staticmethod
    def _gen_reference():
        return f'KS{uuid.uuid4().hex[:12].upper()}'

    @staticmethod
    def initiate_payment(livraison, operateur, numero):
        """Crée ou récupère un objet PaiementMobile de manière idempotente.

        Retourne le modèle `PaiementMobile`.
        """
        if operateur not in dict(PaiementMobile.OPERATEUR_CHOICES):
            raise PaymentError('Opérateur invalide')

        reference = PaymentService._gen_reference()

        # Créer le paiement dans une transaction atomique
        with transaction.atomic():
            # Si un paiement existe déjà et est final, éviter duplication
            try:
                existing = PaiementMobile.objects.select_for_update().get(livraison=livraison)
                # si déjà en success, on renvoie l'existant
                if existing.statut == PaiementMobile.STATUT_SUCCESS:
                    logger.info('Paiement existant déjà confirmé: %s', existing.reference)
                    return existing
                # sinon on réutilise la référence existante
                reference = existing.reference or reference
            except PaiementMobile.DoesNotExist:
                existing = None

            paiement, created = PaiementMobile.objects.update_or_create(
                livraison=livraison,
                defaults={
                    'operateur': operateur,
                    'numero_telephone': numero,
                    'montant': livraison.cout_estime,
                    'reference': reference,
                    'statut': PaiementMobile.STATUT_PENDING,
                }
            )

        # Simulation / appel réel
        if settings.DEBUG:
            # Simuler: créer transaction_id et marquer SUCCESS après un court délai simulé
            paiement.transaction_id = f'SIM-{uuid.uuid4().hex[:20]}'
            paiement.statut = PaiementMobile.STATUT_SUCCESS
            paiement.date_confirmation = timezone.now()
            paiement.save(update_fields=['transaction_id','statut','date_confirmation'])
            livraison.est_paye = True
            livraison.save(update_fields=['est_paye'])
            logger.info('Paiement simulé réussi %s', paiement.reference)
            return paiement

        # Placeholder: appeler l'API opérateur ici (implementer selon SDK)
        # Pour l'instant on lève une erreur indiquant non-implémenté
        raise PaymentError('Mode production non configuré pour les API opérateurs')

    @staticmethod
    def _find_payment(reference=None, transaction_id=None):
        if not reference and not transaction_id:
            raise PaymentError('reference ou transaction_id requis')
        try:
            if transaction_id:
                return PaiementMobile.objects.get(transaction_id=transaction_id)
            return PaiementMobile.objects.get(reference=reference)
        except PaiementMobile.DoesNotExist:
            raise PaymentError('Paiement introuvable')

    @staticmethod
    def update_status(reference=None, transaction_id=None, statut=PaiementMobile.STATUT_FAILED):
        paiement = PaymentService._find_payment(reference=reference, transaction_id=transaction_id)
        with transaction.atomic():
            if paiement.statut == statut:
                return paiement
            if paiement.statut == PaiementMobile.STATUT_SUCCESS and statut != PaiementMobile.STATUT_SUCCESS:
                logger.warning('Tentative de rétrogradation du paiement %s depuis SUCCESS vers %s', paiement.reference, statut)
                return paiement
            paiement.statut = statut
            if statut == PaiementMobile.STATUT_SUCCESS:
                paiement.date_confirmation = timezone.now()
                paiement.save(update_fields=['statut', 'date_confirmation'])
                livraison = paiement.livraison
                livraison.est_paye = True
                livraison.save(update_fields=['est_paye'])
            else:
                paiement.save(update_fields=['statut'])
            return paiement

    @staticmethod
    def confirm_payment(reference=None, transaction_id=None):
        """Confirmer un paiement par reference ou transaction_id de manière idempotente."""
        return PaymentService.update_status(
            reference=reference,
            transaction_id=transaction_id,
            statut=PaiementMobile.STATUT_SUCCESS,
        )

    @staticmethod
    def fail_payment(reference=None, transaction_id=None):
        return PaymentService.update_status(
            reference=reference,
            transaction_id=transaction_id,
            statut=PaiementMobile.STATUT_FAILED,
        )
