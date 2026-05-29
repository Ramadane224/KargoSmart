from django.contrib import admin
from .models import Conversation, Message, LectureMessage


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('livraison', 'date_creation', 'date_derniere_activite')
    list_filter = ('date_creation',)
    search_fields = ('livraison__code_livraison',)
    filter_horizontal = ('participants',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('auteur', 'conversation', 'est_lu', 'date_envoi')
    list_filter = ('est_lu', 'date_envoi')
    search_fields = ('contenu', 'auteur__username')
    readonly_fields = ('date_envoi',)


@admin.register(LectureMessage)
class LectureMessageAdmin(admin.ModelAdmin):
    list_display = ('message', 'lecteur', 'date_lecture')
    list_filter = ('date_lecture',)
    search_fields = ('lecteur__username',)
