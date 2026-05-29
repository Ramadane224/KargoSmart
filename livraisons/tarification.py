import math

TARIF_MINIMUM_GNF = 15_000


def calculer_tarif_distance(distance_km: float) -> int:
    """Retourne le tarif de base en GNF selon la distance."""
    if distance_km <= 2:
        return 15_000
    elif distance_km <= 5:
        return int(15_000 + (distance_km - 2) * 4_000)
    elif distance_km <= 10:
        return int(27_000 + (distance_km - 5) * 3_500)
    elif distance_km <= 20:
        return int(44_500 + (distance_km - 10) * 3_000)
    else:
        return int(74_500 + (distance_km - 20) * 2_500)


def calculer_supplement_poids(poids_kg: float) -> int:
    """Retourne le supplément poids en GNF."""
    if poids_kg <= 5:
        return 0
    elif poids_kg <= 15:
        return 5_000
    elif poids_kg <= 30:
        return 15_000
    elif poids_kg <= 50:
        return 30_000
    else:
        return 50_000


def calculer_supplement_type(type_colis: str) -> int:
    """Retourne le supplément selon le type de colis en GNF."""
    supplements = {
        'STANDARD':    0,
        'DOCUMENT':   -2_000,
        'ALIMENTAIRE': 5_000,
        'FRAGILE':    10_000,
        'VOLUMINEUX': 20_000,
    }
    return supplements.get(type_colis, 0)


def arrondir_au_millier(montant: int) -> int:
    """Arrondit au millier supérieur."""
    return math.ceil(montant / 1000) * 1000


def calculer_cout_livraison(
    distance_km: float,
    poids_kg: float = 0,
    type_colis: str = 'STANDARD',
    est_fragile: bool = False,
) -> dict:
    """
    Calcule le coût total d'une livraison en GNF.
    Retourne un dictionnaire avec le détail et le total.
    """
    if not distance_km or distance_km <= 0:
        distance_km = 1.0

    poids_kg = poids_kg or 0

    tarif_base = calculer_tarif_distance(distance_km)
    supp_poids = calculer_supplement_poids(poids_kg)
    supp_type = calculer_supplement_type(type_colis)
    supp_fragile = 8_000 if est_fragile else 0

    total_brut = tarif_base + supp_poids + supp_type + supp_fragile
    total_final = arrondir_au_millier(max(total_brut, TARIF_MINIMUM_GNF))

    return {
        'tarif_base': tarif_base,
        'supp_poids': supp_poids,
        'supp_type': supp_type,
        'supp_fragile': supp_fragile,
        'total': total_final,
        'distance_km': round(distance_km, 2),
        'poids_kg': poids_kg,
    }
