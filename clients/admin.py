from django.contrib import admin
from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
	list_display = ['nom', 'prenom', 'telephone', 'email', 'quartier', 'est_actif', 'date_creation']
	search_fields = ['nom', 'prenom', 'telephone']
	list_filter = ['est_actif', 'quartier']
	readonly_fields = ['date_creation']
