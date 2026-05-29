from django.contrib import admin

from .models import Profil, ProfilLivreur


@admin.register(Profil)
class ProfilAdmin(admin.ModelAdmin):
    list_display = ['username', 'role', 'telephone', 'est_verifie', 'date_creation']
    list_filter = ['role', 'est_verifie']
    search_fields = ['username', 'telephone']
    actions = ['activer_comptes', 'desactiver_comptes']

    def activer_comptes(self, request, queryset):
        queryset.update(est_verifie=True)
        self.message_user(request, 'Comptes activés avec succès.')
    activer_comptes.short_description = 'Activer les comptes sélectionnés'

    def desactiver_comptes(self, request, queryset):
        queryset.update(est_verifie=False)
        self.message_user(request, 'Comptes désactivés avec succès.')
    desactiver_comptes.short_description = 'Désactiver les comptes sélectionnés'


@admin.register(ProfilLivreur)
class ProfilLivreurAdmin(admin.ModelAdmin):
    list_display = ['profil', 'type_vehicule', 'note_moyenne', 'est_disponible', 'est_actif']
    list_filter = ['type_vehicule', 'est_actif', 'est_disponible']
    actions = ['valider_livreurs']

    def valider_livreurs(self, request, queryset):
        queryset.update(est_actif=True)
        self.message_user(request, 'Livreurs validés avec succès.')
    valider_livreurs.short_description = 'Valider les livreurs sélectionnés'
