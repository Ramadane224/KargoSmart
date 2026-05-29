from django.urls import path
from . import views

urlpatterns = [
    path('', views.ListeConversationsView.as_view(), name='liste_conversations'),
    path('<int:pk>/', views.DetailConversationView.as_view(), name='detail_conversation'),
    path('<int:conversation_pk>/envoyer/', views.envoyer_message, name='envoyer_message'),
]
