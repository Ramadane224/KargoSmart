import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.views.generic import ListView, DetailView
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from utilisateurs.permissions import est_gestionnaire, est_livreur, est_client
from .models import Conversation, Message, LectureMessage


class ListeConversationsView(LoginRequiredMixin, ListView):
    """Liste les conversations de l'utilisateur."""
    model = Conversation
    template_name = 'conversations/conversation_list.html'
    context_object_name = 'conversations'
    paginate_by = 20

    def get_queryset(self):
        return Conversation.objects.filter(participants=self.request.user).select_related('livraison__client', 'livraison__livreur__profil')


class DetailConversationView(LoginRequiredMixin, DetailView):
    """Affiche une conversation complète."""
    model = Conversation
    template_name = 'conversations/conversation_detail.html'
    context_object_name = 'conversation'

    def get_queryset(self):
        return Conversation.objects.filter(participants=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        conversation = self.object
        ctx['messages'] = conversation.messages.select_related('auteur').all()
        
        # Marquer les messages comme lus
        unread_messages = conversation.messages.filter(est_lu=False).exclude(auteur=self.request.user)
        for msg in unread_messages:
            msg.est_lu = True
            msg.save(update_fields=['est_lu'])
        
        return ctx


@require_http_methods(["POST"])
def envoyer_message(request, conversation_pk):
    """Envoie un message dans une conversation (AJAX)."""
    conversation = get_object_or_404(Conversation, pk=conversation_pk)
    
    if request.user not in conversation.participants.all():
        return JsonResponse({'erreur': 'Accès refusé'}, status=403)
    
    try:
        data = json.loads(request.body)
        contenu = data.get('contenu', '').strip()
        
        if not contenu:
            return JsonResponse({'erreur': 'Message vide'}, status=400)
        
        message = Message.objects.create(
            conversation=conversation,
            auteur=request.user,
            contenu=contenu,
            est_lu=True
        )
        
        conversation.save()
        
        return JsonResponse({
            'success': True,
            'message': {
                'id': message.id,
                'auteur': message.auteur.get_full_name() or message.auteur.username,
                'contenu': message.contenu,
                'date_envoi': message.date_envoi.strftime('%d/%m/%Y %H:%M:%S'),
            }
        })
    except Exception as e:
        return JsonResponse({'erreur': str(e)}, status=400)
