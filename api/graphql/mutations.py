import logging
from decimal import Decimal

import graphene
from django.utils.crypto import get_random_string
from graphene import relay

from api.graphql.types import BrokerNode, ServiceProvider, ServiceProviderNode
from trader.enums import MarketSession, OrderAction
from trader.models import Account, ProviderSession, TradingStrategy
from trader.providers import Etrade
from trader.utils import get_limit_price

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
        provider_id = graphene.ID(required=True)
        oauth_verifier = graphene.String(required=True)

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
        provider_id = graphene.ID(required=True)

    broker = graphene.Field(BrokerNode)

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

        default_account = Account.objects.filter(
            institution_type='BROKERAGE').first()

        provider.account_key = default_account.account_key
        provider.save()

        return SyncAccounts(broker=provider.broker)


class BuyStockError(graphene.Enum):
    ACCOUNT_NOT_PROVIDED = 'ACCOUNT_NOT_PROVIDED'


class BuyStock(relay.ClientIDMutation):
    class Input:
        provider_id = graphene.ID(required=True)
        strategy_id = graphene.ID(required=True)
        symbol = graphene.String(required=True)
        account_id = graphene.ID()

    error = graphene.Field(BuyStockError)
    error_message = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, symbol, strategy_id, provider_id, account_id=None):
        strategy = TradingStrategy.objects.get(id=strategy_id)
        provider = ServiceProvider.objects.select_related('session') \
            .get(id=provider_id)
        account = Account.objects.get(id=account_id) if account_id else None
        account_key = account.account_key.strip() if account \
            else provider.account_key.strip()

        if not account_key:
            return BuyStock(
                error=BuyStockError.ACCOUNT_NOT_PROVIDED,
                error_message='Either specify an accountId that has a valid accountKey ' +
                'or configure a default accountKey on the provider.'
            )

        if not account:
            account = Account.objects.get(account_key=account_key)

        order_client_id = get_random_string(length=20)

        etrade = Etrade(provider)
        last_price = etrade.get_price(symbol)

        limit_price = get_limit_price(OrderAction.BUY, last_price,
                                      strategy.price_margin)

        order_params = {
            'account_key': account_key,
            'order_client_id': order_client_id,
            'market_session': MarketSession.current().value,
            'action': OrderAction.BUY.value,
            'symbol': symbol,
            'quantity': strategy.get_quantity_for(
                buying_power=account.cash_buying_power, price_per_share=last_price),
            'limit_price': limit_price
        }

        preview_ids = etrade.preview_order(**order_params)
        etrade.place_order(preview_ids=preview_ids, **order_params)

        return BuyStock()


class SellStockError(graphene.Enum):
    ACCOUNT_NOT_PROVIDED = 'ACCOUNT_NOT_PROVIDED'


class SellStock(relay.ClientIDMutation):
    class Input:
        provider_id = graphene.ID(required=True)
        symbol = graphene.String(required=True)
        account_id = graphene.ID()

    error = graphene.Field(SellStockError)
    error_message = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, symbol, provider_id, account_id=None):
        account = Account.objects.get(id=account_id) if account_id else None
        provider = ServiceProvider.objects.select_related('session') \
            .get(id=provider_id)
        account_key = account.account_key.strip() if account \
            else provider.account_key.strip()

        if not account_key:
            return SellStock(
                error=SellStockError.ACCOUNT_NOT_PROVIDED,
                error_message='Either specify an accountId that has a valid accountKey ' +
                'or configure a default accountKey on the provider.'
            )

        order_client_id = get_random_string(length=20)

        etrade = Etrade(provider)
        position_quantity = etrade.get_position_quantity(account_key, symbol)
        last_price = etrade.get_price(symbol)

        order_params = {
            'account_key': account_key,
            'order_client_id': order_client_id,
            'market_session': MarketSession.current().value,
            'action': OrderAction.SELL.value,
            'symbol': symbol,
            'quantity': position_quantity,
            'limit_price': get_limit_price(OrderAction.SELL, last_price, margin=Decimal('0.02'))
        }

        preview_ids = etrade.preview_order(**order_params)
        etrade.place_order(preview_ids=preview_ids, **order_params)

        return SellStock()


class CancelOrderError(graphene.Enum):
    ACCOUNT_NOT_PROVIDED = 'ACCOUNT_NOT_PROVIDED'


class CancelOrder(relay.ClientIDMutation):
    class Input:
        provider_id = graphene.ID(required=True)
        order_id = graphene.ID(required=True)
        account_id = graphene.ID()

    error = graphene.Field(CancelOrderError)
    error_message = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, order_id, provider_id, account_id=None):
        account = Account.objects.get(id=account_id) if account_id else None
        provider = ServiceProvider.objects.select_related('session') \
            .get(id=provider_id)
        account_key = account.account_key.strip() if account \
            else provider.account_key.strip()

        if not account_key:
            return CancelOrder(
                error=CancelOrderError.ACCOUNT_NOT_PROVIDED,
                error_message='Either specify an accountId that has a valid accountKey ' +
                'or configure a default accountKey on the provider.'
            )

        etrade = Etrade(provider)
        etrade.cancel_order(
            account_key=account_key,
            order_id=order_id
        )

        return CancelOrder()


class Mutation(graphene.ObjectType):
    connect_provider = ConnectProvider.Field(required=True)
    authorize_connection = AuthorizeConnection.Field(required=True)
    sync_accounts = SyncAccounts.Field(required=True)
    buy_stock = BuyStock.Field(required=True)
    sell_stock = SellStock.Field(required=True)
    cancel_order = CancelOrder.Field(required=True)
