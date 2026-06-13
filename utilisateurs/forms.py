from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Profil, ProfilLivreur, Role


class ConnexionForm(AuthenticationForm):
    username = forms.CharField(label='Identifiant', widget=forms.TextInput(attrs={'class': 'rounded border-slate-300 p-2 w-full'}))
    password = forms.CharField(label='Mot de passe', widget=forms.PasswordInput(attrs={'class': 'rounded border-slate-300 p-2 w-full'}))


class InscriptionForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=[(r.value, r.label) for r in Role if r != Role.ADMINISTRATEUR],
        initial=Role.GESTIONNAIRE
    )

    class Meta:
        model = get_user_model()
        fields = [
            'username',
            'email',
            'telephone',
            'first_name',
            'last_name',
            'role',
            'password1',
            'password2',
        ]
        widgets = {
            'role': forms.Select(attrs={'class': 'rounded border-slate-300 p-2 w-full'}),
        }


class ProfilUpdateForm(forms.ModelForm):
    class Meta:
        model = Profil
        fields = ['telephone', 'adresse', 'photo']
        widgets = {
            'telephone': forms.TextInput(attrs={'class': 'rounded border-slate-300 p-2 w-full'}),
            'adresse': forms.Textarea(attrs={'class': 'rounded border-slate-300 p-2 w-full', 'rows': 3}),
        }


class AdminUserForm(forms.ModelForm):
    """Formulaire admin pour créer/modifier un utilisateur."""
    password = forms.CharField(
        label='Mot de passe',
        widget=forms.PasswordInput,
        required=False,
        help_text='Laisser vide pour ne pas changer.',
    )

    class Meta:
        model = Profil
        fields = ['username', 'first_name', 'last_name', 'email', 'telephone', 'role', 'adresse', 'est_verifie']

    def save(self, commit=True):
        user = super().save(commit=False)
        pwd = self.cleaned_data.get('password')
        if pwd:
            user.set_password(pwd)
        if commit:
            user.save()
        return user


class LivreurInscriptionForm(forms.ModelForm):
    class Meta:
        model = ProfilLivreur
        fields = ['photo_identite', 'photo_permis', 'type_vehicule', 'mobile_money_num']
        widgets = {
            'type_vehicule': forms.Select(attrs={'class': 'rounded border-slate-300 p-2 w-full'}),
            'mobile_money_num': forms.TextInput(attrs={'class': 'rounded border-slate-300 p-2 w-full'}),
        }
