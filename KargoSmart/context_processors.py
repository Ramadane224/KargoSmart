from django.utils import timezone


def notifications_non_lues(request):
    if request.user.is_authenticated:
        count = request.user.notifications.filter(est_lue=False).count()
        notifs = request.user.notifications.filter(est_lue=False)[:5]
        return {'notifs_count': count, 'notifs_recentes': notifs}
    return {'notifs_count': 0, 'notifs_recentes': []}
