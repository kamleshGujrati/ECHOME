# accounts/views_auth.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from .decorators import custom_login_required
from django.contrib.auth.hashers import make_password, check_password
from .models import User, UserSession,faildedLoginAttempt
from .session import create_session_for_user, revoke_session_by_cookie , parse_cookie_token
from .signals import user_logged_in, user_logged_out
from .forms import RegisterForm, LoginForm  # if you have these; else use request.POST

COOKIE_NAME = getattr(settings, "SESSION_COOKIE_NAME", "XSESSIONID")
COOKIE_TTL = getattr(settings, "SESSION_TTL_SECONDS", 7 * 24 * 3600)

def signup(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            u = User(
                username = cd["username"],
                email = cd.get("email", ""),
                full_name = cd.get("full_name", ""),
            )
            # hash password field into password_hash attribute expected by your model
            u.password_hash = make_password(cd["password"])
            u.save()
            # Auto-login: create session
            token, us = create_session_for_user(request, u)
            resp = redirect("homepage")
            resp.set_cookie(COOKIE_NAME, token, httponly=True, samesite="Lax", max_age=COOKIE_TTL, secure=not settings.DEBUG)
            # fire signal
            user_logged_in.send(sender=None, user=u, request=request, session=us)
            return resp
        return render(request, "accounts/signup.html", {"form": form})
    else:
        form = RegisterForm()
    return render(request, "accounts/signup.html", {"form": form})

def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data["identifier"]
            password = form.cleaned_data["password"]
            # find user by email or username (use your backend logic)
            user = User.objects.filter(email__iexact=identifier).first() or User.objects.filter(username__iexact=identifier).first()
            if not user:
                form.add_error(None, "Invalid credentials")
                return render(request, "accounts/login.html", {"form": form})

            # check password
            if not user.password_hash or not check_password(password, user.password_hash):
                #  failed attempt
                user.increment_attempts()
                faildedLoginAttempt.objects.create(user=user, user_agent=request.META.get("USER_AGENT",''), ip_address=request.META.get('REMOTE_ADDR', ''))
                form.add_error(None, "Invalid credentials")

                return render(request, "accounts/login.html", {"form": form})
            # check if frozen
            if user.is_frozen():
                form.add_error(None, "Account is temporarily frozen due to multiple failed login attempts. Please try again later.")
                return render(request, "accounts/login.html", {"form": form})
            # successful login
            user.reset_attempts()
            token, us = create_session_for_user(request, user)
            resp = redirect(request.GET.get("next") or "homepage")
            resp.set_cookie(COOKIE_NAME, token, httponly=True, samesite="Lax", max_age=COOKIE_TTL, secure=not settings.DEBUG)
            # print("Set cookie:", COOKIE_NAME, token)
            # print("User logged in:", user)

            # fire login signal
            user_logged_in.send(sender=None, user=user, request=request, session=us)
            return resp
    else:
        form = LoginForm()
    return render(request, "accounts/login.html", {"form": form})

@custom_login_required
def logout_view(request):
    cookie_val = request.COOKIES.get(COOKIE_NAME)
    session = None
    try:
        session = None
        if cookie_val:
            # attempt to map cookie to session
            # parse cookie via helpers (we can try fetching UserSession)

            parsed = parse_cookie_token(cookie_val)
            if parsed:
                session_key = parsed[0]

                session = UserSession.objects.filter(session_key=session_key).first()
            # mark revoked
            revoke_session_by_cookie(cookie_val)
    finally:
        # fire logout signal
        if session:
            user_logged_out.send(sender=None, user=session.user, request=request, session=session)

    resp = redirect("homepage")
    resp.delete_cookie(COOKIE_NAME)
    return resp

# def profile(request):
#     if not request.custom_user:
#         return redirect("login")
#     return render(request, "accounts/profile.html", {"user": request.custom_user})