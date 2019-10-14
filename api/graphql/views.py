from django.contrib.auth.mixins import AccessMixin, LoginRequiredMixin
from graphene_django.views import GraphQLView
from django.views.decorators.csrf import csrf_exempt
from rest_framework.authentication import TokenAuthentication
from rest_framework import exceptions
from django.http.response import HttpResponse


class TokenAuthRequiredMixin(AccessMixin):
    """Verify that the current user is authenticated."""

    def dispatch(self, request, *args, **kwargs):
        authenticator = TokenAuthentication()
        try:
            auth_result = authenticator.authenticate(request)
        except exceptions.AuthenticationFailed as e:
            return HttpResponse(content=str(e), status=e.status_code)

        if not auth_result:
            return HttpResponse(content="Missing Token", status=401)

        request.user = auth_result[0]

        if not request.user.is_authenticated:
            return self.handle_no_permission()
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
