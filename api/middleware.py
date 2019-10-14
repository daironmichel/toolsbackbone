from django.conf import settings
from django.http.response import HttpResponse
from django.http.request import HttpRequest
from django.contrib.auth.middleware import AuthenticationMiddleware
from graphene_django.debug import DjangoDebugMiddleware


class AuthorizationMiddleware:
    def __init__(self, get_response=None):
        self.get_response = get_response
        super().__init__()

    def __call__(self, request: HttpRequest):
        # for k, v in request.META.items():
        #     print(f'{k}: {v}')
        # if request.path.startswith('/api') and not request.path.startswith('/api/graphql/'):
        #     app_name = request.META.get('HTTP_X_APP_NAME', '')
        #     app_key = request.META.get('HTTP_X_APP_KEY', '')

        #     lock = getattr(settings, 'AUTHORIZED_APPS', {})

        #     if app_name not in lock:
        #         return HttpResponse(status=401, content='Invalid App!')

        #     if lock.get(app_name) != app_key:
        #         return HttpResponse(status=401, content='Invalid Key!')
        # authenticator = BearerTokenAuthentication()
        # user, token = authenticator.authenticate(request)
        # request.user = user

        return self.get_response(request)
