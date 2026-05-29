from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, View

from .models import Notification


class ListeNotificationsView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'notifications/liste.html'
    context_object_name = 'notifications'

    def get_queryset(self):
        return Notification.objects.filter(destinataire=self.request.user).order_by('-date_creation')


class LireNotificationView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        notification = get_object_or_404(Notification, pk=pk, destinataire=request.user)
        notification.est_lue = True
        notification.save()
        return redirect(reverse_lazy('liste_notifications'))
