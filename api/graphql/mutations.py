import logging
from datetime import datetime
from decimal import Decimal

import graphene
from django.utils.crypto import get_random_string
from graphene import relay

from api.graphql.types import (BrokerNode, ServiceProvider,
                               ServiceProviderNode, SettingsNode)
from trader.enums import MarketSession, OrderAction, PriceType
from trader.models import (Account, AutoPilotTask, ProviderSession, Settings,
                           TradingStrategy)
from trader.providers import get_provider_instance
from trader.utils import get_limit_price, get_round_price

# pylint: disable=invalid-name
logger = logging.getLogger("trader.api")


def get_autopilot(user_id: int, symbol: str) -> AutoPilotTask:
    return AutoPilotTask.objects.filter(
        user_id=user_id, symbol=symbol).first()


def turn_off_autopilot(user_id: int, symbol: str) -> bool:
    autopilot = get_autopilot(user_id, symbol)

    if not autopilot:
        return False

    autopilot.signal = AutoPilotTask.MANUAL_OVERRIDE
    autopilot.save()
    return True


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

        etrade = get_provider_instance(provider)
        authorize_url = etrade.get_authorize_url()

        return ConnectProvider(service_provider=provider, authorize_url=authorize_url,
                               callback_enabled=provider.callback_configured)


class AuthorizeConnectionError(graphene.Enum):
    PROVIDER_NOT_FOUND = 'PROVIDER_NOT_FOUND'
    INCOMPATIBLE_STATE = 'INCOMPATIBLE_STATE'
    MISSING_REQUIRED_FIELD = 'MISSING_REQUIRED_FIELD'


class AuthorizeConnection(relay.ClientIDMutation):
    class Input:
        oauth_verifier = graphene.String(required=True)
        oauth_token = graphene.String()
        provider_id = graphene.ID()

    service_provider = graphene.Field(ServiceProviderNode)

    error = graphene.Field(AuthorizeConnectionError)
    error_message = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, oauth_verifier,
                               oauth_token=None, provider_id=None):
        if not oauth_token and not provider_id:
            return AuthorizeConnection(error=AuthorizeConnectionError.MISSING_REQUIRED_FIELD,
                                       error_message="Provide oath_token or provider_id")

        if oauth_token:
            provider = info.context.user.service_providers \
                .filter(session__request_token=oauth_token) \
                .select_related('session') \
                .first()
        else:
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

        etrade = get_provider_instance(provider)
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

        etrade = get_provider_instance(provider)
        etrade.sync_accounts()

        default_account = Account.objects.filter(
            institution_type='BROKERAGE').first()

        if not provider.account_key:
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
        price = graphene.Decimal()
        account_id = graphene.ID()
        autopilot = graphene.Boolean()

    error = graphene.Field(BuyStockError)
    error_message = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, symbol, strategy_id, provider_id,
                               price=0, account_id=None, autopilot=False):
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

        if autopilot:
            task = AutoPilotTask(
                signal=AutoPilotTask.BUY,
                user=info.context.user,
                strategy=strategy,
                provider=provider,
                account=account,
                symbol=symbol,
                quantity=0,
                entry_price=price,
                base_price=price,
                ref_price=price,
                ref_time=datetime.now)
            task.save()
            return BuyStock()

        etrade = get_provider_instance(provider)
        last_price = Decimal(price) if price else etrade.get_bid_price(symbol)

        limit_price = get_limit_price(OrderAction.BUY, last_price,
                                      strategy.price_margin)
        quantity = strategy.get_quantity_for(
            buying_power=account.cash_buying_power, price_per_share=last_price)

        order_params = {
            'account_key': account_key,
            'market_session': MarketSession.current().value,
            'action': OrderAction.BUY.value,
            'symbol': symbol,
            'price_type': PriceType.LIMIT.value,
            'quantity': quantity,
            'limit_price': limit_price
        }

        preview_ids = etrade.preview_order(
            order_client_id=get_random_string(length=20), **order_params)
        etrade.place_order(order_client_id=get_random_string(length=20),
                           preview_ids=preview_ids, **order_params)

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

        turn_off_autopilot(info.context.user.id, symbol)

        etrade = get_provider_instance(provider)
        position_quantity = etrade.get_position_quantity(account_key, symbol)
        last_price = etrade.get_ask_price(symbol)

        order_params = {
            'account_key': account_key,
            'market_session': MarketSession.current().value,
            'action': OrderAction.SELL.value,
            'symbol': symbol,
            'price_type': PriceType.LIMIT.value,
            'quantity': position_quantity,
            'limit_price': get_limit_price(OrderAction.SELL, last_price, margin=Decimal('0.01'))
        }

        preview_ids = etrade.preview_order(
            order_client_id=get_random_string(length=20), **order_params)
        etrade.place_order(order_client_id=get_random_string(
            length=20), preview_ids=preview_ids, **order_params)

        return SellStock()


class PlaceStopLossError(graphene.Enum):
    ACCOUNT_NOT_PROVIDED = 'ACCOUNT_NOT_PROVIDED'
    NOT_ALLOWED_ON_AUTOPILOT = 'NOT_ALLOWED_ON_AUTOPILOT'


class PlaceStopLoss(relay.ClientIDMutation):
    class Input:
        provider_id = graphene.ID(required=True)
        symbol = graphene.String(required=True)
        account_id = graphene.ID()

    error = graphene.Field(PlaceStopLossError)
    error_message = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, symbol, provider_id, account_id=None):
        account = Account.objects.get(id=account_id) if account_id else None
        provider = ServiceProvider.objects.select_related('session') \
            .get(id=provider_id)
        account_key = account.account_key.strip() if account \
            else provider.account_key.strip()

        if not account_key:
            return PlaceStopLoss(
                error=PlaceStopLossError.ACCOUNT_NOT_PROVIDED,
                error_message='Either specify an accountId that has a valid accountKey ' +
                'or configure a default accountKey on the provider.'
            )

        autopilot = get_autopilot(info.context.user.id, symbol)
        if autopilot:
            return PlaceStopLoss(
                error=PlaceStopLossError.NOT_ALLOWED_ON_AUTOPILOT,
                error_message='You must turn off autopilot first.'
            )

        etrade = get_provider_instance(provider)
        position_quantity = etrade.get_position_quantity(account_key, symbol)
        last_price = etrade.get_ask_price(symbol)
        stop_price = get_round_price(
            last_price - (last_price * Decimal('0.023')))
        limit_price = get_limit_price(
            OrderAction.SELL, stop_price, margin=Decimal('0.01'))

        order_params = {
            'account_key': account_key,
            'market_session': MarketSession.current().value,
            'action': OrderAction.SELL.value,
            'symbol': symbol,
            'price_type': PriceType.STOP_LIMIT.value,
            'quantity': position_quantity,
            'stop_price': stop_price,
            'limit_price': limit_price
        }

        preview_ids = etrade.preview_order(
            order_client_id=get_random_string(length=20), **order_params)
        etrade.place_order(order_client_id=get_random_string(
            length=20), preview_ids=preview_ids, **order_params)

        return PlaceStopLoss()


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

        etrade = get_provider_instance(provider)
        etrade.cancel_order(
            account_key=account_key,
            order_id=order_id
        )

        return CancelOrder()


class SaveSettingsError(graphene.Enum):
    INVALID_REFRESH_RATE = 'INVALID_REFRESH_RATE'
    DEFAULT_BROKER_REQUIRED = 'DEFAULT_BROKER_REQUIRED'
    DEFAULT_PROVIDER_REQUIRED = 'DEFAULT_PROVIDER_REQUIRED'


class SaveSettings(relay.ClientIDMutation):
    class Input:
        refresh_rate = graphene.Int(
            description='Data refresh rate in milliseconds.')
        default_broker_id = graphene.ID()
        default_provider_id = graphene.ID()
        default_account_id = graphene.ID()

    error = graphene.Field(SaveSettingsError)
    error_message = graphene.String()

    settings = graphene.Field(SettingsNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, refresh_rate=None, default_broker_id=None,
                               default_provider_id=None, default_account_id=None):
        if refresh_rate is not None and refresh_rate < 0:
            return SaveSettings(
                error=SaveSettingsError.INVALID_REFRESH_RATE,
                error_message='Refresh rate must be >= 0'
            )

        if default_provider_id and not default_broker_id:
            return SaveSettings(
                error=SaveSettingsError.DEFAULT_BROKER_REQUIRED,
                error_message='Default broker required to set default provider'
            )

        if default_account_id and not default_provider_id:
            return SaveSettings(
                error=SaveSettingsError.DEFAULT_PROVIDER_REQUIRED,
                error_message='Default provider required to set default account'
            )

        user = info.context.user
        settings = Settings.objects.filter(user=user).first()
        if not settings:
            settings = Settings(user=user)

        default_broker = None
        if default_broker_id:
            default_borker = user.brokers.get(id=default_broker_id)
        default_provider = None
        if default_provider_id:
            default_provider = user.service_providers.get(
                id=default_provider_id)
        default_account = None
        if default_account_id:
            default_account = user.accounts.get(id=default_account_id)

        if refresh_rate is not None and refresh_rate >= 0:
            settings.refresh_rate = refresh_rate

        if default_broker:
            settings.default_broker = default_borker

        settings.save()

        if default_provider and default_broker:
            default_broker.default_provider = default_provider
            default_broker.save()

        if default_account and default_provider:
            default_provider.account_key = default_account.account_key
            default_provider.save()

        return SaveSettings(settings=settings)


class AutoPilotONError(graphene.Enum):
    PROVIDER_REQUIRED = 'PROVIDER_REQUIRED'
    ACCOUNT_REQUIRED = 'ACCOUNT_REQUIRED'
    STRATEGY_REQUIRED = 'STRATEGY_REQUIRED'
    NO_POSITION_FOR_SYMBOL = 'NO_POSITION_FOR_SYMBOL'


class AutoPilotON(relay.ClientIDMutation):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._settings = None

    class Input:
        symbol = graphene.String(required=True)
        strategy_id = graphene.ID()
        provider_id = graphene.ID()
        account_id = graphene.ID()

    error = graphene.Field(AutoPilotONError)
    error_message = graphene.String()

    def _get_settings(self, user):
        if not self._settings:
            self._settings = Settings.objects.filter(user_id=user.id) \
                .select_related('default_stategy', 'default_broker__default_provider') \
                .first()
        return self._settings

    def get_default_strategy(self, user):
        settings = self._get_settings(user)
        if not settings:
            return None
        return settings.default_strategy

    def get_default_provider(self, user):
        settings = self._get_settings(user)
        if not settings:
            return None
        return settings.default_broker.default_provider

    def get_default_account(self, user):
        settings = self._get_settings(user)
        if not settings:
            return None
        default_provider = self._default_provider(user)
        if not default_provider:
            return None
        return Account.objects.filter(account_key=default_provider.account_key)

    @classmethod
    def mutate_and_get_payload(cls, root, info, symbol, strategy_id=None,
                               provider_id=None, account_id=None):

        user = info.context.user

        strategy = user.strategies.get(
            id=strategy_id) if strategy_id else root.get_default_strategy(user)
        if not strategy:
            return AutoPilotON(error=AutoPilotONError.STRATEGY_REQUIRED,
                               error_message='Either set the strategy_id param or configure a default.')

        provider = user.providers.get(
            id=provider_id) if provider_id else root.get_default_privider(user)
        if not provider:
            return AutoPilotON(error=AutoPilotONError.PROVIDER_REQUIRED,
                               error_message='Either set the provider_id param or configure a default.')

        account = user.accounts.get(
            id=account_id) if account_id else root.get_default_account(user)
        if not account:
            return AutoPilotON(error=AutoPilotONError.ACCOUNT_REQUIRED,
                               error_message='Either set the account_id param or configure a default.')

        etrade = get_provider_instance(provider)
        quantity, entry_price = etrade.get_position(account.symbol, symbol)
        if not quantity or not entry_price:
            return AutoPilotON(error=AutoPilotONError.NO_POSITION_FOR_SYMBOL,
                               error_message=f'No position found for {symbol}. Position: {quantity}@{entry_price}')

        task = AutoPilotTask(
            user=user,
            strategy=strategy,
            provider=provider,
            account=account,
            symbol=symbol,
            quantity=quantity,
            entry_price=entry_price,
            base_price=entry_price,
            ref_price=entry_price,
            ref_time=datetime.now)

        task.save()
        return AutoPilotON()


class AutoPilotOFFError(graphene.Enum):
    NO_AUTOPILOT = 'NO_AUTOPILOT'


class AutoPilotOFF(relay.ClientIDMutation):
    class Input:
        symbol = graphene.String(required=True)

    error = graphene.Field(AutoPilotOFFError)
    error_message = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, symbol):
        user = info.context.user

        success = turn_off_autopilot(user.id, symbol)

        if not success:
            return AutoPilotOFF(error=AutoPilotOFFError.NO_AUTOPILOT,
                                error_message=f'No autopilot active for {symbol}')

        return AutoPilotOFF()


class Mutation(graphene.ObjectType):
    connect_provider = ConnectProvider.Field(required=True)
    authorize_connection = AuthorizeConnection.Field(required=True)
    sync_accounts = SyncAccounts.Field(required=True)
    buy_stock = BuyStock.Field(required=True)
    sell_stock = SellStock.Field(required=True)
    place_stop_loss = PlaceStopLoss.Field(required=True)
    cancel_order = CancelOrder.Field(required=True)
    save_settings = SaveSettings.Field(required=True)
    autopilot_ON = AutoPilotON.Field(required=True)
    autopilot_OFF = AutoPilotOFF.Field(required=True)
