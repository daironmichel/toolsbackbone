from django.conf import settings
from django.contrib.auth import login
from django.http.request import HttpRequest
from django.http.response import HttpResponse
from graphene_django.debug import DjangoDebugMiddleware
from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication


class TokenAuthMiddleware:
    def __init__(self, get_response=None):
        self.get_response = get_response
        super().__init__()

    def __call__(self, request: HttpRequest):
        print('HTTP_AUTHORIZATION:', request.META.get(
            'HTTP_AUTHORIZATION', None))
        # if request.user.is_authenticated:
        #     return self.get_response(request)

        # authenticator = TokenAuthentication()
        # try:
        #     auth_result = authenticator.authenticate(request)
        # except exceptions.AuthenticationFailed:
        #     return self.get_response(request)

        # if not auth_result:
        #     return self.get_response(request)

        # user = auth_result[0]

        # login(request, user)

        return self.get_response(request)
