from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http.request import HttpRequest
from django.http.response import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from graphene_django.views import GraphQLView
from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication


class TokenAuthRequiredMixin(LoginRequiredMixin):
    """Authenticate the user using token auth and 
    verify that the user was authenticated."""

    permission_denied_message = 'Authorization token required.'
    raise_exception = True

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        if request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        authenticator = TokenAuthentication()
        try:
            auth_result = authenticator.authenticate(request)
            if not auth_result:
                return self.handle_no_permission()
        except exceptions.AuthenticationFailed as e:
            return HttpResponse(content=str(e), status=e.status_code)
        except PermissionDenied as e:
            return HttpResponseForbidden(content=str(e))

        user, token = auth_result
        request.user = user
        request.auth = token

        return super().dispatch(request, *args, **kwargs)


class TokenAuthGraphQLView(TokenAuthRequiredMixin, GraphQLView):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view.cls = cls
        view.initkwargs = initkwargs

        # Note: session based authentication is explicitly CSRF validated,
        # all other authentication is CSRF exempt.
        return csrf_exempt(view)


class PrivateGraphQLView(LoginRequiredMixin, GraphQLView):
    pass
