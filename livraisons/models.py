from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
import math


def haversine_km(lat1, lon1, lat2, lon2):
    """Calcule la distance en km entre deux points GPS (formule Haversine)."""
    R = 6371
    phi1, phi2 = math.radians(float(lat1)), math.radians(float(lat2))
    dphi = math.radians(float(lat2) - float(lat1))
    dlambda = math.radians(float(lon2) - float(lon1))
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class StatutLivraison(models.TextChoices):
    EN_ATTENTE = 'EN_ATTENTE', 'En attente'
    ASSIGNEE = 'ASSIGNEE', 'Assignée'
    EN_ROUTE = 'EN_ROUTE', 'En route'
    EN_COURS = 'EN_COURS', 'En cours'
    PROCHE_DESTINATION = 'PROCHE_DESTINATION', 'Proche destination'
    LIVREE = 'LIVREE', 'Livrée'
    ANNULEE = 'ANNULEE', 'Annulée'
    ECHOUEE = 'ECHOUEE', 'Échec de livraison'


class TypeColis(models.TextChoices):
    DOCUMENT = 'DOCUMENT', 'Document'
    ALIMENTAIRE = 'ALIMENTAIRE', 'Alimentaire'
    FRAGILE = 'FRAGILE', 'Fragile'
    STANDARD = 'STANDARD', 'Standard'
    VOLUMINEUX = 'VOLUMINEUX', 'Volumineux'


class Livraison(models.Model):
    code_livraison = models.CharField(max_length=10, unique=True)
    client = models.ForeignKey('clients.Client', on_delete=models.PROTECT, related_name='livraisons')
    livreur = models.ForeignKey('utilisateurs.ProfilLivreur', null=True, blank=True, on_delete=models.SET_NULL, related_name='livraisons')
    createur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='livraisons_creees')

    adresse_depart = models.TextField()
    quartier_depart = models.CharField(max_length=100, null=True, blank=True)
    latitude_depart = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude_depart = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    adresse_arrivee = models.TextField()
    quartier_arrivee = models.CharField(max_length=100, null=True, blank=True)
    point_repere = models.TextField(null=True, blank=True)
    latitude_arrivee = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude_arrivee = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    description_colis = models.TextField()
    type_colis = models.CharField(max_length=20, choices=TypeColis.choices, default=TypeColis.STANDARD)
    poids_estime_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    est_fragile = models.BooleanField(default=False)

    statut = models.CharField(max_length=20, choices=StatutLivraison.choices, default=StatutLivraison.EN_ATTENTE)

    cout_estime = models.DecimalField(max_digits=12, decimal_places=0)
    cout_final = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True)
    distance_km = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    duree_estimee_min = models.PositiveSmallIntegerField(null=True, blank=True)
    mode_paiement = models.CharField(
        max_length=10,
        choices=[
            ('ORANGE', 'Orange Money'),
            ('MTN', 'MTN MoMo'),
            ('ESPECES', 'Espèces'),
        ],
        default='ESPECES',
    )
    est_paye = models.BooleanField(default=False)

    date_creation = models.DateTimeField(auto_now_add=True)
    date_assignation = models.DateTimeField(null=True, blank=True)
    date_livraison_reelle = models.DateTimeField(null=True, blank=True)
    date_livraison_prevue = models.DateField(null=True, blank=True)

    code_confirmation = models.CharField(max_length=6, null=True, blank=True)
    photo_preuve = models.ImageField(upload_to='preuves/', null=True, blank=True)
    notes_livreur = models.TextField(null=True, blank=True)
    note_client = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )

    class Meta:
        db_table = 'ks_livraisons_livraison'
        ordering = ['-date_creation']

    def __str__(self):
        return f"{self.code_livraison} - {self.get_statut_display()}"


class HistoriqueLivraison(models.Model):
    livraison = models.ForeignKey(Livraison, on_delete=models.CASCADE, related_name='historique')
    ancien_statut = models.CharField(max_length=20, null=True, blank=True)
    nouveau_statut = models.CharField(max_length=20)
    modifie_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    commentaire = models.TextField(null=True, blank=True)
    date_changement = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ks_livraisons_historique'
        ordering = ['-date_changement']

    def __str__(self):
        return f"Historique {self.livraison.code_livraison} -> {self.nouveau_statut}"


class PositionLivreur(models.Model):
    """Stocke la dernière position GPS connue d'un livreur."""
    livreur = models.OneToOneField(
        'utilisateurs.ProfilLivreur',
        on_delete=models.CASCADE,
        related_name='position_gps',
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    livraison_en_cours = models.ForeignKey(
        Livraison,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='positions_livreur',
    )
    progression = models.PositiveSmallIntegerField(default=0)  # 0-100 %
    date_mise_a_jour = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ks_livraisons_position_livreur'

    def __str__(self):
        return f"Position {self.livreur} ({self.latitude}, {self.longitude})"


class PaiementMobile(models.Model):
    """Simule un paiement Orange Money / MTN MoMo."""

    OPERATEUR_CHOICES = [('ORANGE', 'Orange Money'), ('MTN', 'MTN MoMo')]
    STATUT_CHOICES = [
        ('EN_ATTENTE', 'En attente'),
        ('CONFIRME', 'Confirmé'),
        ('ECHOUE', 'Échoué'),
        ('REMBOURSE', 'Remboursé'),
    ]

    livraison = models.OneToOneField(Livraison, on_delete=models.CASCADE, related_name='paiement')
    operateur = models.CharField(max_length=10, choices=OPERATEUR_CHOICES)
    numero_telephone = models.CharField(max_length=20)
    montant = models.DecimalField(max_digits=12, decimal_places=0)
    reference = models.CharField(max_length=20, unique=True)
    statut = models.CharField(max_length=15, choices=STATUT_CHOICES, default='EN_ATTENTE')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_confirmation = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ks_livraisons_paiement_mobile'

    def __str__(self):
        return f"{self.operateur} {self.numero_telephone} — {self.montant} GNF ({self.statut})"
