from django import forms

from .models import Client


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['nom', 'prenom', 'telephone', 'email', 'adresse', 'quartier', 'commune', 'notes_internes', 'est_actif']
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'rounded-xl border border-slate-200 px-3 py-2 w-full text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'prenom': forms.TextInput(attrs={
                'class': 'rounded-xl border border-slate-200 px-3 py-2 w-full text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'telephone': forms.TextInput(attrs={
                'class': 'rounded-xl border border-slate-200 px-3 py-2 w-full text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'rounded-xl border border-slate-200 px-3 py-2 w-full text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'adresse': forms.Textarea(attrs={
                'class': 'rounded-xl border border-slate-200 px-3 py-2 w-full text-sm focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 2
            }),
            'quartier': forms.TextInput(attrs={
                'class': 'rounded-xl border border-slate-200 px-3 py-2 w-full text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'commune': forms.TextInput(attrs={
                'class': 'rounded-xl border border-slate-200 px-3 py-2 w-full text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'notes_internes': forms.Textarea(attrs={
                'class': 'rounded-xl border border-slate-200 px-3 py-2 w-full text-sm focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 3
            }),
            'est_actif': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 rounded text-blue-600'
            }),
        }
