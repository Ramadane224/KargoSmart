from groq import Groq
import json as json_module

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View

from django.db.models import Count
from livraisons.models import Livraison, StatutLivraison
from utilisateurs.models import ProfilLivreur

SYSTEM_PROMPT = """
Tu es KargoBot, l'assistant intelligent de la plateforme KargoSmart, spécialisé
dans la gestion de livraisons urbaines à Conakry, Guinée.
Tu peux aider à : comprendre les statuts de livraison, conseiller sur l'optimisation
des tournées, répondre aux questions sur les paiements Orange Money / MTN MoMo,
interpréter les données du tableau de bord, guider l'utilisation de la plateforme.
Réponds toujours en français, de façon concise et professionnelle (max 3 phrases).
Ne donne jamais d'informations confidentielles sur d'autres utilisateurs.
"""


class AIAssistantView(LoginRequiredMixin, View):
    def post(self, request):
        body = json_module.loads(request.body or '{}')
        message = body.get('message', '').strip()
        history = body.get('history', []) or []

        if not message:
            return JsonResponse({'error': 'Message vide'}, status=400)

        context_data = self._get_user_context(request.user)

        messages = []
        for msg in history[-10:]:
            if msg.get('role') in ('user', 'assistant') and msg.get('content'):
                messages.append({'role': msg['role'], 'content': msg['content']})

        user_message = message
        if context_data:
            user_message = f"[Contexte: {context_data}]\n{message}"
        messages.append({'role': 'user', 'content': user_message})

        try:
            client = Groq(api_key=settings.GROQ_API_KEY)
            response = client.chat.completions.create(
                model='llama-3.1-8b-instant',
                max_tokens=400,
                temperature=0.7,
                messages=[{'role': 'system', 'content': SYSTEM_PROMPT}] + messages,
            )
            reply = response.choices[0].message.content
            return JsonResponse({'response': reply, 'role': 'assistant'})

        except Exception as e:
            return JsonResponse(
                {'error': f'Erreur IA : {str(e)}'},
                status=500,
            )

    def _get_user_context(self, user):
        role = getattr(user, 'role', '')
        try:
            if role == 'ADMINISTRATEUR':
                counts = {
                    row['statut']: row['n']
                    for row in Livraison.objects.values('statut').annotate(n=Count('id'))
                }
                total = sum(counts.values())
                en_attente = counts.get('EN_ATTENTE', 0)
                en_route = counts.get('EN_ROUTE', 0) + counts.get('EN_COURS', 0)
                livrees = counts.get('LIVREE', 0)
                return (
                    f"Admin. Total: {total} livraisons, "
                    f"En attente: {en_attente}, En route: {en_route}, Livrées: {livrees}"
                )
            elif role == 'LIVREUR':
                livreur = user.profil_livreur
                actives = livreur.livraisons.filter(
                    statut__in=['EN_ROUTE', 'EN_COURS', 'PROCHE_DESTINATION'],
                ).count()
                return (
                    f"Livreur: {user.get_full_name()}, "
                    f"véhicule: {livreur.type_vehicule}, "
                    f"livraisons actives: {actives}, "
                    f"note moyenne: {livreur.note_moyenne}"
                )
            elif role == 'GESTIONNAIRE':
                en_attente = Livraison.objects.filter(statut='EN_ATTENTE').count()
                return f"Gestionnaire: {user.get_full_name()}, livraisons en attente: {en_attente}"
        except Exception:
            pass
        return f"Utilisateur: {user.get_full_name()}, rôle: {role}"
