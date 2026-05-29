from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from clients.models import Client
from livraisons.models import Livraison, PositionLivreur, StatutLivraison, haversine_km
from notifications.models import Notification
from utilisateurs.models import ProfilLivreur
from .serializers import (
    ClientSerializer,
    LivraisonSerializer,
    NotificationSerializer,
    PositionLivreurSerializer,
    ProfilLivreurSerializer,
)


class EstLivreur(BasePermission):
    message = 'Accès réservé aux livreurs.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'role', None) == 'LIVREUR'
        )


class EstAdminOuGestionnaire(BasePermission):
    message = 'Accès réservé aux administrateurs et gestionnaires.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'role', None) in ['ADMINISTRATEUR', 'GESTIONNAIRE']
        )


class LivraisonViewSet(viewsets.ModelViewSet):
    queryset = Livraison.objects.select_related('client', 'livreur__profil').all()
    serializer_class = LivraisonSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        statut = self.request.query_params.get('statut')
        if statut:
            qs = qs.filter(statut=statut)
        return qs

    @action(detail=False, methods=['get'])
    def en_cours(self, request):
        """Livraisons actives pour la carte."""
        qs = self.get_queryset().filter(
            statut__in=[
                StatutLivraison.ASSIGNEE,
                StatutLivraison.EN_ROUTE,
                StatutLivraison.EN_COURS,
                StatutLivraison.PROCHE_DESTINATION,
            ]
        )
        return Response(LivraisonSerializer(qs, many=True).data)


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        telephone = self.request.query_params.get('telephone')
        if telephone:
            qs = qs.filter(telephone__icontains=telephone)
        return qs


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(destinataire=self.request.user)

    @action(detail=True, methods=['post'])
    def marquer_lue(self, request, pk=None):
        notif = self.get_object()
        notif.est_lue = True
        notif.save()
        return Response({'status': 'ok'})

    @action(detail=False, methods=['post'])
    def tout_lire(self, request):
        self.get_queryset().filter(est_lue=False).update(est_lue=True)
        return Response({'status': 'ok'})


# ─── GPS ──────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated, EstLivreur])
def mettre_a_jour_position(request):
    """
    Reçoit la position GPS d'un livreur et met à jour PositionLivreur.
    Body JSON : { lat, lng, livraison_id (opt), progression (opt) }
    """
    try:
        livreur = request.user.profil_livreur
    except ProfilLivreur.DoesNotExist:
        return Response({'error': 'Utilisateur non livreur'}, status=status.HTTP_403_FORBIDDEN)

    lat = request.data.get('lat')
    lng = request.data.get('lng')
    if lat is None or lng is None:
        return Response({'error': 'lat et lng requis'}, status=status.HTTP_400_BAD_REQUEST)

    livraison_id = request.data.get('livraison_id')
    progression = request.data.get('progression', 0)

    livraison = None
    if livraison_id:
        try:
            livraison = Livraison.objects.get(pk=livraison_id, livreur=livreur)
        except Livraison.DoesNotExist:
            return Response({'error': 'Livraison introuvable pour ce livreur.'}, status=status.HTTP_404_NOT_FOUND)

        if livraison.statut not in [
            StatutLivraison.EN_ROUTE,
            StatutLivraison.EN_COURS,
            StatutLivraison.PROCHE_DESTINATION,
        ]:
            return Response(
                {'error': 'La livraison doit être en route, en cours ou proche de destination pour mettre à jour la position.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    position, _ = PositionLivreur.objects.update_or_create(
        livreur=livreur,
        defaults={
            'latitude': lat,
            'longitude': lng,
            'livraison_en_cours': livraison,
            'progression': min(int(progression), 100),
        },
    )
    return Response(PositionLivreurSerializer(position).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated, EstAdminOuGestionnaire])
def positions_livreurs_actifs(request):
    """Retourne toutes les positions des livreurs actifs (pour la carte dashboard)."""
    positions = PositionLivreur.objects.select_related(
        'livreur__profil', 'livraison_en_cours'
    ).filter(livreur__est_actif=True)
    return Response(PositionLivreurSerializer(positions, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tracking_livraison(request, pk):
    """Retourne la position GPS du livreur pour une livraison donnée."""
    livraison = Livraison.objects.select_related('livreur__profil').get(pk=pk)
    data = LivraisonSerializer(livraison).data
    if livraison.livreur:
        try:
            pos = livraison.livreur.position_gps
            data['position_livreur'] = PositionLivreurSerializer(pos).data
        except PositionLivreur.DoesNotExist:
            data['position_livreur'] = None
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated, EstAdminOuGestionnaire])
def meilleur_livreur(request, livraison_pk):
    """
    Retourne le livreur disponible le plus proche du point de départ.
    Logique : distance Haversine entre position GPS livreur et départ livraison.
    """
    livraison = Livraison.objects.get(pk=livraison_pk)
    if not livraison.latitude_depart or not livraison.longitude_depart:
        # Fallback : livreur avec le moins de livraisons actives
        livreur = (
            ProfilLivreur.objects.filter(est_actif=True, est_disponible=True)
            .order_by('total_livraisons')
            .first()
        )
        if not livreur:
            return Response({'error': 'Aucun livreur disponible'}, status=404)
        return Response(ProfilLivreurSerializer(livreur).data)

    positions = PositionLivreur.objects.select_related('livreur__profil').filter(
        livreur__est_actif=True, livreur__est_disponible=True
    )
    meilleur = None
    dist_min = float('inf')
    for pos in positions:
        d = haversine_km(
            livraison.latitude_depart, livraison.longitude_depart,
            pos.latitude, pos.longitude,
        )
        if d < dist_min:
            dist_min = d
            meilleur = pos.livreur

    if not meilleur:
        return Response({'error': 'Aucun livreur disponible'}, status=404)

    result = ProfilLivreurSerializer(meilleur).data
    result['distance_km'] = round(dist_min, 2)
    result['duree_estimee_min'] = int((dist_min / 25) * 60)
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated, EstAdminOuGestionnaire])
def suggerer_livreur(request):
    """
    Suggère le livreur disponible le plus proche d'une coordonnée donnée.
    Params: lat (latitude), lon (longitude)
    """
    try:
        lat = float(request.GET.get('lat'))
        lon = float(request.GET.get('lon'))
    except (TypeError, ValueError):
        return Response({'error': 'Paramètres lat/lon invalides'}, status=400)
    
    # Chercher les livreurs actifs avec position GPS
    positions = PositionLivreur.objects.select_related('livreur__profil').filter(
        livreur__est_actif=True, livreur__est_disponible=True
    )
    
    if not positions.exists():
        # Fallback: livreur avec le moins de livraisons actives
        livreur = (
            ProfilLivreur.objects.filter(est_actif=True, est_disponible=True)
            .order_by('total_livraisons')
            .first()
        )
        if not livreur:
            return Response({'error': 'Aucun livreur disponible'}, status=404)
        return Response(ProfilLivreurSerializer(livreur).data)
    
    meilleur = None
    dist_min = float('inf')
    for pos in positions:
        d = haversine_km(lat, lon, pos.latitude, pos.longitude)
        if d < dist_min:
            dist_min = d
            meilleur = pos.livreur
    
    if not meilleur:
        return Response({'error': 'Aucun livreur disponible'}, status=404)
    
    result = ProfilLivreurSerializer(meilleur).data
    result['distance_km'] = round(dist_min, 2)
    result['duree_estimee_min'] = int((dist_min / 25) * 60)
    return Response(result)


# ─── TARIFICATION / SIMULATION DE PRIX ───────────────────────────────────────
from livraisons.tarification import calculer_cout_livraison


@api_view(['GET'])
@permission_classes([IsAuthenticated, EstAdminOuGestionnaire])
def simuler_prix(request):
    try:
        if all(request.GET.get(k) for k in ['lat1','lon1','lat2','lon2']):
            distance_km = haversine_km(
                float(request.GET['lat1']), float(request.GET['lon1']),
                float(request.GET['lat2']), float(request.GET['lon2']),
            )
        else:
            distance_km = float(request.GET.get('distance_km', 1))

        poids_kg = float(request.GET.get('poids_kg', 0))
        type_colis = request.GET.get('type_colis', 'STANDARD')
        est_fragile = request.GET.get('est_fragile', 'false').lower() == 'true'

        resultat = calculer_cout_livraison(distance_km, poids_kg, type_colis, est_fragile)

        def formater_gnf(valeur):
            return f"{int(valeur):,} GNF".replace(',', ' ')

        return Response({
            **resultat,
            'total_formate': formater_gnf(resultat['total']),
            'tarif_base_formate': formater_gnf(resultat['tarif_base']),
            'supp_poids_formate': formater_gnf(resultat['supp_poids']),
            'supp_type_formate': formater_gnf(resultat['supp_type']),
            'supp_fragile_formate': formater_gnf(resultat['supp_fragile']),
        })
    except (ValueError, TypeError) as e:
        return Response({'erreur': f'Paramètre invalide : {str(e)}'}, status=400)
