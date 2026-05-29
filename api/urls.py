from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .ai_assistant import AIAssistantView
from .views import (
    ClientViewSet,
    LivraisonViewSet,
    NotificationViewSet,
    mettre_a_jour_position,
    positions_livreurs_actifs,
    tracking_livraison,
    meilleur_livreur,
    simuler_prix,
)
from .geolocalisation import (
    geocoder_adresse,
    calculer_itineraire,
    position_reelle_livreur,
)

router = DefaultRouter()
router.register('livraisons', LivraisonViewSet, basename='api-livraison')
router.register('clients', ClientViewSet, basename='api-client')
router.register('notifications', NotificationViewSet, basename='api-notification')

urlpatterns = [
    # Patterns spécifiques AVANT le router (pour éviter capture)
    path('simuler-prix/', simuler_prix, name='simuler_prix'),
    # GPS
    path('gps/position/', mettre_a_jour_position, name='api-gps-position'),
    path('gps/livreurs/', positions_livreurs_actifs, name='api-gps-livreurs'),
    path('gps/tracking/<int:pk>/', tracking_livraison, name='api-gps-tracking'),
    path('gps/meilleur-livreur/<int:livraison_pk>/', meilleur_livreur, name='api-gps-meilleur-livreur'),
    path('assistant/', AIAssistantView.as_view(), name='ai_assistant'),
    # Geo
    path('geo/geocoder/', geocoder_adresse, name='geocoder_adresse'),
    path('geo/itineraire/', calculer_itineraire, name='calculer_itineraire'),
    path('gps/position-reelle/', position_reelle_livreur, name='position_reelle'),
    # Router (doit être DERNIER)
    path('', include(router.urls)),
]
