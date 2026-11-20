from django.shortcuts import redirect
from django.conf import settings

LOGIN_URL ='/accounts/login/'

def custom_login_required(view_func):
    def _wrapped(request, *args, **kwargs):

        # use your custom user loaded by CustomAuthMiddleware
        user = getattr(request, "custom_user", None)

        if not user:
            return redirect(f"/accounts/login/?next={request.path}")

        return view_func(request, *args, **kwargs)

    return _wrapped
 