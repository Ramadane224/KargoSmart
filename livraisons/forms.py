from django import forms

from utilisateurs.models import ProfilLivreur
from .models import Livraison, StatutLivraison


class LivraisonForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'cout_estime' in self.fields:
            self.fields['cout_estime'].required = False
            self.fields['cout_estime'].widget = forms.HiddenInput()

    class Meta:
        model = Livraison
        fields = [
            'client',
            'adresse_depart',
            'quartier_depart',
            'latitude_depart',
            'longitude_depart',
            'adresse_arrivee',
            'quartier_arrivee',
            'point_repere',
            'latitude_arrivee',
            'longitude_arrivee',
            'description_colis',
            'type_colis',
            'poids_estime_kg',
            'est_fragile',
            'cout_estime',
            'mode_paiement',
            'date_livraison_prevue',
            'notes_livreur',
        ]
        widgets = {
            'date_livraison_prevue': forms.DateInput(attrs={'type': 'date'}),
            'description_colis': forms.Textarea(attrs={'rows': 3}),
            'point_repere': forms.Textarea(attrs={'rows': 2}),
            'latitude_depart': forms.HiddenInput(),
            'longitude_depart': forms.HiddenInput(),
            'latitude_arrivee': forms.HiddenInput(),
            'longitude_arrivee': forms.HiddenInput(),
        }


class AssignationForm(forms.Form):
    livreur = forms.ModelChoiceField(
        queryset=ProfilLivreur.objects.filter(est_actif=True, est_disponible=True),
        label='Livreur disponible',
    )


class ChangerStatutForm(forms.Form):
    nouveau_statut = forms.ChoiceField(choices=StatutLivraison.choices, label='Nouveau statut')
    commentaire = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2}),
        required=False,
        label='Commentaire',
    )
