import logging

import graphene
from graphene import relay

from api.graphql.types import (AccountNode, BrokerNode, ServiceProvider,
                               ServiceProviderNode)
from trader.models import Account, Order, ProviderSession, TradingStrategy
from trader.providers import Etrade

# pylint: disable=invalid-name
logger = logging.getLogger("trader.api")


class ConnectProviderError(graphene.Enum):
    PROVIDER_NOT_FOUND = "PROVIDER_NOT_FOUND"


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
    PROVIDER_NOT_FOUND = 'PROVIDER_NOT_FOUND'
    INCOMPATIBLE_STATE = 'INCOMPATIBLE_STATE'


class AuthorizeConnection(relay.ClientIDMutation):
    class Input:
        provider_id = graphene.ID()
        aouth_verifier = graphene.String()

    service_provider = graphene.Field(ServiceProviderNode)

    error = graphene.Field(AuthorizeConnectionError)
    error_message = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, provider_id, oauth_verifier):
        provider = info.context.user.service_providers \
            .filter(id=provider_id) \
            .select_related('session') \
            .first()

        if not provider:
            return AuthorizeConnection(error=AuthorizeConnectionError.SESSION_NOT_FOUND,
                                       error_message="Pending session not found. Try starting a new connection.")

        if provider.session.status != ProviderSession.REQUESTING:
            return AuthorizeConnection(error=AuthorizeConnectionError.INCOMPATIBLE_STATE,
                                       error_message="Session state is not compatible. Try starting a new connection.")

        etrade = Etrade(provider)
        provider = etrade.authorize(oauth_verifier)

        return AuthorizeConnection(service_provider=provider)


class SyncAccountsError(graphene.Enum):
    PROVIDER_NOT_FOUND = 'PROVIDER_NOT_FOUND'


class SyncAccounts(relay.ClientIDMutation):
    class Input:
        provider_id = graphene.ID()

    boker = graphene.Field(BrokerNode)

    error = graphene.Field(AuthorizeConnectionError)
    error_message = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, provider_id):
        provider = info.context.user.service_providers \
            .filter(id=provider_id) \
            .select_related('session') \
            .first()

        if not provider:
            return AuthorizeConnection(error=SyncAccounts.PROVIDER_NOT_FOUND,
                                       error_message="Pending session not found. Try starting a new connection.")

        etrade = Etrade(provider)
        etrade.sync_accounts()

        return SyncAccounts(broker=provider.broker)


class BuyStockError(graphene.Enum):
    INVALID = 1


class BuyStock(relay.ClientIDMutation):
    class Input:
        symbol = graphene.String()
        strategy_id = graphene.ID()
        account_id = graphene.ID()
        provider_id = graphene.ID()

    account = graphene.Field(AccountNode)

    error = graphene.Field(AuthorizeConnectionError)
    error_message = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, symbol, strategy_id, account_id, provider_id):
        account = Account.objects.get(id=account_id)
        strategy = TradingStrategy.objects.get(id=strategy_id)
        provider = ServiceProvider.objects.get(id=provider_id)
        order = Order.objects.create()

        etrade = Etrade(provider)

        account_key = account.account_key
        order_client_id,
        market_session
        action,
        symbol,
        quantity,
        limit_price
        preview_ids


class Mutation(graphene.ObjectType):
    connect_provider = ConnectProvider.Field()
    authorize_connection = AuthorizeConnection.Field()
    sync_accounts = SyncAccounts.Field()
    buy_stock = BuyStock.Field()
