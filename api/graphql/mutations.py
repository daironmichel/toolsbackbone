import logging

import graphene
from graphene import relay
from rauth import OAuth1Service

from api.graphql.types import ServiceProviderNode
from trader.models import ProviderSession

logger = logging.getLogger("api")


class ConnectProviderError(graphene.Enum):
    PROVIDER_NOT_FOUND = 1


class ConnectProvider(relay.ClientIDMutation):
    class Input:
        provider_id = graphene.ID(required=True)

    service_provider = graphene.Field(ServiceProviderNode)
    authorize_url = graphene.String()
    callback_enabled = graphene.Boolean()

    error = graphene.Field(ConnectProviderError)
    error_message = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, provider_id):
        provider = info.context.user.service_providers.filter(
            id=provider_id).first()

        if not provider:
            return ConnectProvider(
                error=ConnectProviderError.PROVIDER_NOT_FOUND,
                error_message="Sorry! the provider you're trying to connect to was not found."
            )

        service = OAuth1Service(
            name=provider.name,
            consumer_key=provider.consumer_key,
            consumer_secret=provider.consumer_secret,
            request_token_url=provider.request_token_url,
            access_token_url=provider.access_token_url,
            authorize_url=provider.authorize_url,
            base_url=provider.base_url
        )

        request_token, request_token_secret = service.get_request_token(
            params={"oauth_callback": "oob", "format": "json"})
        authorize_url = f'{service.authorize_url}?key={service.consumer_key}&token={request_token}'

        if provider.session:
            provider.session.delete()
        provider.session = ProviderSession.objects.create(
            request_token=request_token, request_token_secret=request_token_secret)
        provider.save()

        return ConnectProvider(service_provider=provider, authorize_url=authorize_url, callback_enabled=False)


class AuthorizeConnectionError(graphene.Enum):
    PENDING_SESSION_NOT_FOUND = 1
    MULTIPLE_PENDING_SESSIONS_FOUND = 2


class AuthorizeConnection(relay.ClientIDMutation):
    class Input:
        aouth_verifier = graphene.String()

    service_provider = graphene.Field(ServiceProviderNode)

    error = graphene.Field(AuthorizeConnectionError)
    error_message = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, oauth_verifier):
        provider = info.context.user.service_providers.filter()


class Mutation(graphene.ObjectType):
    connect_provider = ConnectProvider.Field()
