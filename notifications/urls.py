from django.urls import path

from .views import ListeNotificationsView, LireNotificationView

urlpatterns = [
    path('', ListeNotificationsView.as_view(), name='liste_notifications'),
    path('<int:pk>/lire/', LireNotificationView.as_view(), name='lire_notification'),
]
