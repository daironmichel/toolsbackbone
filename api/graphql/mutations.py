import logging
import uuid

import graphene
from django.db import transaction
from graphene import relay

from api.graphql.types import (AccountNode, BrokerNode, ServiceProvider,
                               ServiceProviderNode)
from trader.models import Account, Order, ProviderSession, TradingStrategy
from trader.providers import Etrade, MarketSession, OrderAction

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

    error = graphene.Field(BuyStockError)
    error_message = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, symbol, strategy_id, account_id, provider_id):
        account = Account.objects.get(id=account_id)
        strategy = TradingStrategy.objects.get(id=strategy_id)
        provider = ServiceProvider.objects.get(id=provider_id) \
            .select_related('session')

        order_client_id = uuid.uuid4()

        etrade = Etrade(provider)
        last_price = etrade.get_price(symbol)

        order_params = {
            'account_key': account.account_key,
            'order_client_id': order_client_id,
            'market_session': MarketSession.current(),
            'action': OrderAction.BUY,
            'symbol': symbol,
            'quantity': strategy.get_quatity_for(
                buying_power=account.cash_buying_power, price_per_share=last_price),
            'limit_price': strategy.get_limit_price(OrderAction.BUY, last_price)
        }

        preview_ids = etrade.preview_order(**order_params)
        etrade.place_order(preview_ids=preview_ids, **order_params)

        return BuyStock(account=account)


class SellStockError(graphene.Enum):
    INVALID = 1


class SellStock(relay.ClientIDMutation):
    class Input:
        symbol = graphene.String()
        account_id = graphene.ID()
        provider_id = graphene.ID()

    account = graphene.Field(AccountNode)

    error = graphene.Field(SellStockError)
    error_message = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, symbol, account_id, provider_id):
        account = Account.objects.get(id=account_id)
        provider = ServiceProvider.objects.get(id=provider_id) \
            .select_related('session')

        order_client_id = uuid.uuid4()

        etrade = Etrade(provider)
        position_quantity = etrade.get_position_quantity(
            account.account_key, symbol)
        last_price = etrade.get_price(symbol)

        order_params = {
            'account_key': account.account_key,
            'order_client_id': order_client_id,
            'market_session': MarketSession.current(),
            'action': OrderAction.SELL,
            'symbol': symbol,
            'quantity': position_quantity,
            'limit_price': strategy.get_limit_price(OrderAction.SELL, last_price)
        }

        preview_ids = etrade.preview_order(**order_params)
        etrade.place_order(preview_ids=preview_ids, **order_params)

        return SellStock(account=account)


class CancelOrderError(graphene.Enum):
    INVALID = 1


class CancelOrder(relay.ClientIDMutation):
    class Input:
        account_id = graphene.ID()
        order_id = graphene.ID()
        provider_id = graphene.ID()

    account = graphene.Field(AccountNode)

    error = graphene.Field(CancelOrderError)
    error_message = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, account_id, order_id, provider_id):
        account = Account.objects.get(id=account_id)
        provider = ServiceProvider.objects.get(id=provider_id) \
            .select_related('session')

        etrade = Etrade(provider)
        etrade.cancel_order(
            account_key=account.account_key,
            order_id=order_id
        )

        return CancelOrder(account=account)


class Mutation(graphene.ObjectType):
    connect_provider = ConnectProvider.Field()
    authorize_connection = AuthorizeConnection.Field()
    sync_accounts = SyncAccounts.Field()
    buy_stock = BuyStock.Field()
    cancel_order = CancelOrder.Field()
