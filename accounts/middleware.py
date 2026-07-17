
from accounts.models import User , UserSession
from django.utils.deprecation import MiddlewareMixin
from accounts.session import validate_cookie_token as validate_session_cookie

class CustomAuthMiddleware(MiddlewareMixin):
    """
    Fully custom authentication middleware.
    Loads user from our own cookie + our own UserSession model.
    """
    def process_request(self, request):
        request.custom_user = None
        request.custom_session = None

        cookie = request.COOKIES.get("XSESSIONID")
        # print("middleware cookie:",cookie)
        if not cookie:
            print("No custom session cookie found")
            return

        session = validate_session_cookie(cookie, request)
        # print("valid sessuion :",session)
        if not session:
            print("Invalid session cookie")
            return

        request.custom_session = session
        # print("Authenticated custom user:", session.user)
        request.custom_user = session.user
