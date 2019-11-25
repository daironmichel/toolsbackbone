# pylint: disable=no-member
import logging

import graphene
from graphene import relay
from rauth import OAuth1Service

from api.graphql.types import ServiceProviderNode, AccountNode
from trader.models import ProviderSession
from trader.providers import Etrade

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

        etrade = Etrade(provider)
        authorize_url = etrade.get_authorize_url()

        return ConnectProvider(service_provider=provider, authorize_url=authorize_url, callback_enabled=False)


class AuthorizeConnectionError(graphene.Enum):
    SESSION_NOT_FOUND = 1
    MULTIPLE_SESSIONS = 2
    INCOMPATIBLE_STATE = 3


class AuthorizeConnection(relay.ClientIDMutation):
    class Input:
        request_token = graphene.String()
        aouth_verifier = graphene.String()

    service_provider = graphene.Field(ServiceProviderNode)

    error = graphene.Field(AuthorizeConnectionError)
    error_message = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, request_token, oauth_verifier):
        provider_query = info.context.user.service_providers.filter(
            session__request_token=request_token).select_related('session')

        if provider_query.count() > 1:
            return AuthorizeConnection(error=AuthorizeConnectionError.MULTIPLE_SESSIONS,
                                       error_message="Multiple sessions found. Try starting a new connection.")

        provider = provider_query.first()

        if not provider:
            return AuthorizeConnection(error=AuthorizeConnectionError.SESSION_NOT_FOUND,
                                       error_message="Pending session not found. Try starting a new connection.")

        if provider.session.status != ProviderSession.REQUESTING:
            return AuthorizeConnection(error=AuthorizeConnectionError.INCOMPATIBLE_STATE,
                                       error_message="Session state is not compatible. Try starting a new connection.")

        etrade = Etrade(provider)
        provider = etrade.authorize(oauth_verifier)

        return AuthorizeConnection(service_provider=provider)


class BuyStockError(graphene.Enum):
    INVALID = 1


class BuyStock(relay.ClientIDMutation):
    class Input:
        strategy_id = graphene.ID()
        account_id = graphene.String()

    account = graphene.Field(AccounNode)

    error = graphene.Field(AuthorizeConnectionError)
    error_message = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, request_token, oauth_verifier):


class Mutation(graphene.ObjectType):
    connect_provider = ConnectProvider.Field()
    authorize_connection = AuthorizeConnection.Field()
    buy_stock = BuyStock.Field()
