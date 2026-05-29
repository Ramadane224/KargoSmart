from django.db import models


class Client(models.Model):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20, unique=True)
    email = models.EmailField(null=True, blank=True)
    adresse = models.TextField(null=True, blank=True)
    quartier = models.CharField(max_length=100, null=True, blank=True)
    commune = models.CharField(max_length=50, null=True, blank=True)
    notes_internes = models.TextField(null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    est_actif = models.BooleanField(default=True)

    class Meta:
        db_table = 'ks_clients_client'

    def __str__(self):
        return f"{self.prenom} {self.nom}"
