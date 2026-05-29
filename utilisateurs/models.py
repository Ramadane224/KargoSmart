from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    ADMINISTRATEUR = 'ADMINISTRATEUR', 'Administrateur'
    GESTIONNAIRE = 'GESTIONNAIRE', 'Gestionnaire'
    LIVREUR = 'LIVREUR', 'Livreur'
    CLIENT = 'CLIENT', 'Client'


class Profil(AbstractUser):
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.GESTIONNAIRE)
    telephone = models.CharField(max_length=20, unique=True)
    photo = models.ImageField(upload_to='profils/', null=True, blank=True)
    adresse = models.TextField(null=True, blank=True)
    est_verifie = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modif = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ks_utilisateurs_profil'

    def __str__(self):
        return f"{self.username} ({self.get_full_name() or self.username})"


class ProfilLivreur(models.Model):
    VEHICULE_CHOICES = [
        ('MOTO', 'Moto'),
        ('VOITURE', 'Voiture'),
        ('VELO', 'Vélo'),
    ]

    profil = models.OneToOneField('Profil', on_delete=models.CASCADE, related_name='profil_livreur')
    numero_permis = models.CharField(max_length=50, null=True, blank=True)
    type_vehicule = models.CharField(max_length=10, choices=VEHICULE_CHOICES)
    photo_permis = models.ImageField(upload_to='permis/', null=True, blank=True)
    photo_identite = models.ImageField(upload_to='identites/', null=True, blank=True)
    note_moyenne = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    total_livraisons = models.IntegerField(default=0)
    est_disponible = models.BooleanField(default=False)
    est_actif = models.BooleanField(default=False)
    mobile_money_num = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        db_table = 'ks_utilisateurs_livreur'

    def __str__(self):
        return f"Livreur {self.profil.get_full_name() or self.profil.username}"


class ProfilClient(models.Model):
    """Profil étendu pour les clients enregistrés comme utilisateurs."""
    profil = models.OneToOneField('Profil', on_delete=models.CASCADE, related_name='profil_client')
    date_premiere_livraison = models.DateTimeField(null=True, blank=True)
    total_livraisons = models.IntegerField(default=0)
    note_moyenne = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)

    class Meta:
        db_table = 'ks_utilisateurs_client'

    def __str__(self):
        return f"Client {self.profil.get_full_name() or self.profil.username}"
