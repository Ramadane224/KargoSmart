from rest_framework import serializers

from clients.models import Client
from livraisons.models import Livraison, PositionLivreur
from notifications.models import Notification
from utilisateurs.models import ProfilLivreur


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'nom', 'prenom', 'telephone', 'email', 'adresse', 'quartier', 'commune', 'est_actif']


class ProfilLivreurSerializer(serializers.ModelSerializer):
    nom_complet = serializers.SerializerMethodField()

    class Meta:
        model = ProfilLivreur
        fields = ['id', 'nom_complet', 'type_vehicule', 'note_moyenne', 'est_disponible', 'est_actif', 'total_livraisons']

    def get_nom_complet(self, obj):
        return obj.profil.get_full_name() or obj.profil.username


class LivraisonSerializer(serializers.ModelSerializer):
    client_nom = serializers.SerializerMethodField()
    livreur_nom = serializers.SerializerMethodField()
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)

    class Meta:
        model = Livraison
        fields = [
            'id', 'code_livraison',
            'client', 'client_nom',
            'livreur', 'livreur_nom',
            'adresse_depart', 'latitude_depart', 'longitude_depart',
            'adresse_arrivee', 'latitude_arrivee', 'longitude_arrivee',
            'type_colis', 'statut', 'statut_display',
            'cout_estime', 'distance_km', 'duree_estimee_min',
            'date_creation', 'date_livraison_prevue',
        ]

    def get_client_nom(self, obj):
        return str(obj.client) if obj.client else None

    def get_livreur_nom(self, obj):
        if obj.livreur:
            return obj.livreur.profil.get_full_name() or obj.livreur.profil.username
        return None


class PositionLivreurSerializer(serializers.ModelSerializer):
    livreur_id = serializers.IntegerField(source='livreur.id', read_only=True)
    nom_livreur = serializers.SerializerMethodField()
    vehicule = serializers.CharField(source='livreur.type_vehicule', read_only=True)
    livraison_code = serializers.SerializerMethodField()

    class Meta:
        model = PositionLivreur
        fields = [
            'livreur_id', 'nom_livreur', 'vehicule',
            'latitude', 'longitude', 'progression',
            'livraison_code', 'date_mise_a_jour',
        ]

    def get_nom_livreur(self, obj):
        return obj.livreur.profil.get_full_name() or obj.livreur.profil.username

    def get_livraison_code(self, obj):
        return obj.livraison_en_cours.code_livraison if obj.livraison_en_cours else None


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'destinataire', 'livraison', 'type_notif', 'titre', 'message', 'est_lue', 'date_creation']
