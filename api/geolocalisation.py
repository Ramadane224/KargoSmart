import requests
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

URL_NOMINATIM = "https://nominatim.openstreetmap.org/search"
URL_OSRM = "https://router.project-osrm.org/route/v1/driving"
ENTETES = {"User-Agent": "KargoSmart/1.0 (kargosmart.gn@gmail.com)"}


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def geocoder_adresse(request):
    requete = request.GET.get('q', '').strip()
    if not requete:
        return Response({'erreur': 'Paramètre q requis'}, status=400)

    requete_complete = f"{requete}, Conakry, Guinée"
    parametres = {
        'q': requete_complete,
        'format': 'json',
        'limit': 5,
        'countrycodes': 'gn',
        'addressdetails': 1,
    }

    try:
        reponse = requests.get(URL_NOMINATIM, params=parametres, headers=ENTETES, timeout=5)
        resultats = reponse.json()

        if not resultats:
            parametres.pop('countrycodes')
            reponse = requests.get(URL_NOMINATIM, params=parametres, headers=ENTETES, timeout=5)
            resultats = reponse.json()

        formates = [
            {
                'lat': float(r['lat']),
                'lon': float(r['lon']),
                'nom_complet': r['display_name'],
                'quartier': r.get('address', {}).get('suburb', ''),
                'commune': r.get('address', {}).get('city_district', ''),
            }
            for r in resultats[:5]
        ]
        return Response({'resultats': formates})

    except requests.RequestException as e:
        return Response({'erreur': f'Service de géolocalisation indisponible : {str(e)}'}, status=503)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def calculer_itineraire(request):
    try:
        lat1 = float(request.GET.get('lat1'))
        lon1 = float(request.GET.get('lon1'))
        lat2 = float(request.GET.get('lat2'))
        lon2 = float(request.GET.get('lon2'))
    except (TypeError, ValueError):
        return Response({'erreur': 'lat1, lon1, lat2, lon2 requis (nombres décimaux)'}, status=400)

    url = f"{URL_OSRM}/{lon1},{lat1};{lon2},{lat2}"
    parametres = {
        'overview': 'simplified',
        'geometries': 'geojson',
        'steps': 'false',
    }

    try:
        reponse = requests.get(url, params=parametres, timeout=8)
        donnees = reponse.json()

        if donnees.get('code') != 'Ok' or not donnees.get('routes'):
            from livraisons.models import haversine_km
            dist = haversine_km(lat1, lon1, lat2, lon2)
            return Response({
                'distance_km': round(dist, 2),
                'duree_min': int((dist / 25) * 60),
                'geometrie': None,
                'source': 'haversine',
            })

        itineraire = donnees['routes'][0]
        distance_km = round(itineraire['distance'] / 1000, 2)
        duree_min = int(itineraire['duration'] / 60)
        coordonnees = itineraire['geometry']['coordinates']
        polyline = [[c[1], c[0]] for c in coordonnees]

        return Response({
            'distance_km': distance_km,
            'duree_min': duree_min,
            'geometrie': polyline,
            'source': 'osrm',
        })

    except requests.RequestException:
        from livraisons.models import haversine_km
        dist = haversine_km(lat1, lon1, lat2, lon2)
        return Response({
            'distance_km': round(dist, 2),
            'duree_min': int((dist / 25) * 60),
            'geometrie': None,
            'source': 'haversine',
        })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def position_reelle_livreur(request):
    from livraisons.models import Livraison, PositionLivreur, StatutLivraison
    from utilisateurs.models import ProfilLivreur

    try:
        livreur = request.user.profil_livreur
    except ProfilLivreur.DoesNotExist:
        return Response({'erreur': 'Utilisateur non livreur'}, status=403)

    lat = request.data.get('lat')
    lng = request.data.get('lng')
    precision = request.data.get('precision', 0)

    if lat is None or lng is None:
        return Response({'erreur': 'lat et lng requis'}, status=400)

    livraison_id = request.data.get('livraison_id')
    livraison = None
    if livraison_id:
        try:
            livraison = Livraison.objects.get(
                pk=livraison_id,
                livreur=livreur,
                statut__in=[
                    StatutLivraison.ASSIGNEE,
                    StatutLivraison.EN_ROUTE,
                    StatutLivraison.EN_COURS,
                ]
            )
        except Livraison.DoesNotExist:
            pass

    position, _ = PositionLivreur.objects.update_or_create(
        livreur=livreur,
        defaults={
            'latitude': lat,
            'longitude': lng,
            'livraison_en_cours': livraison,
            'progression': request.data.get('progression', 0),
        },
    )

    return Response({
        'succes': True,
        'lat': float(position.latitude),
        'lng': float(position.longitude),
        'precision': precision,
        'livraison': livraison.code_livraison if livraison else None,
    })
