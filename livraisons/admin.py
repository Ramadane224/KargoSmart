from django.contrib import admin

from .models import Livraison


@admin.register(Livraison)
class LivraisonAdmin(admin.ModelAdmin):
    list_display = ['code_livraison', 'client', 'livreur', 'statut', 'cout_estime', 'date_creation']
    list_filter = ['statut', 'type_colis', 'mode_paiement', 'est_paye']
    search_fields = ['code_livraison', 'client__nom', 'client__telephone']
    readonly_fields = ['code_livraison', 'date_creation']
    date_hierarchy = 'date_creation'
