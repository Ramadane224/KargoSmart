from django import forms

from .models import Client


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['nom', 'prenom', 'telephone', 'email', 'adresse', 'quartier', 'commune']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'rounded border-slate-300 p-2 w-full'}),
            'prenom': forms.TextInput(attrs={'class': 'rounded border-slate-300 p-2 w-full'}),
            'telephone': forms.TextInput(attrs={'class': 'rounded border-slate-300 p-2 w-full'}),
            'email': forms.EmailInput(attrs={'class': 'rounded border-slate-300 p-2 w-full'}),
            'adresse': forms.Textarea(attrs={'class': 'rounded border-slate-300 p-2 w-full', 'rows': 3}),
            'quartier': forms.TextInput(attrs={'class': 'rounded border-slate-300 p-2 w-full'}),
            'commune': forms.TextInput(attrs={'class': 'rounded border-slate-300 p-2 w-full'}),
        }
