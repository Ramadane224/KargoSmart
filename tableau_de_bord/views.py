from datetime import date, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.views.generic import TemplateView

from clients.models import Client
from livraisons.models import Livraison, StatutLivraison
from utilisateurs.models import ProfilLivreur


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'tableau_de_bord/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        counts_qs = Livraison.objects.values('statut').annotate(n=Count('id'))
        counts = {row['statut']: row['n'] for row in counts_qs}
        total = sum(counts.values())
        livrees = counts.get(StatutLivraison.LIVREE, 0)

        today = date.today()
        livraisons_7j = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            livraisons_7j.append({
                'date': day.strftime('%d/%m'),
                'count': Livraison.objects.filter(date_creation__date=day).count()
            })

        context.update({
            'total_livraisons': total,
            'livraisons_en_attente': counts.get(StatutLivraison.EN_ATTENTE, 0),
            'livraisons_assignees': counts.get(StatutLivraison.ASSIGNEE, 0),
            'livraisons_en_route': counts.get(StatutLivraison.EN_ROUTE, 0),
            'livraisons_en_cours': counts.get(StatutLivraison.EN_COURS, 0),
            'livraisons_proche': counts.get(StatutLivraison.PROCHE_DESTINATION, 0),
            'livraisons_terminees': livrees,
            'livraisons_annulees': counts.get(StatutLivraison.ANNULEE, 0),
            'total_livreurs': ProfilLivreur.objects.filter(est_actif=True).count(),
            'total_clients': Client.objects.filter(est_actif=True).count(),
            'livraisons_recentes': Livraison.objects.select_related('client', 'livreur__profil').order_by('-date_creation')[:10],
            'livraisons_7j': livraisons_7j,
            'taux_reussite': round(livrees / total * 100, 1) if total else 0,
        })
        return context
