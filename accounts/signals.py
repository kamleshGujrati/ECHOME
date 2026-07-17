# accounts/signals.py
from django.dispatch import Signal, receiver


user_logged_in = Signal()
user_logged_out = Signal()


@receiver(user_logged_in)
def on_login(sender, user, request, session, **kwargs):
    # Optional: update last_login
    try:
        if hasattr(user, "last_login"):
            from django.utils import timezone
            user.last_login = timezone.now()
            user.save(update_fields=["last_login"])
    except Exception:
        pass


@receiver(user_logged_out)
def on_logout(sender, user, request, session, **kwargs):
    # Optional: cleanup
    pass
