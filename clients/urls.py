from django.urls import path

from .views import CreerClientView, DetailClientView, ListeClientsView, ModifierClientView

urlpatterns = [
    path('', ListeClientsView.as_view(), name='liste_clients'),
    path('creer/', CreerClientView.as_view(), name='creer_client'),
    path('<int:pk>/', DetailClientView.as_view(), name='detail_client'),
    path('<int:pk>/modifier/', ModifierClientView.as_view(), name='modifier_client'),
]
