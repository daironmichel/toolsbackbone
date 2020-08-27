import logging
from datetime import datetime
from decimal import Decimal

import graphene
from django.utils import timezone
from django.utils.crypto import get_random_string
from graphene import relay

from api.graphql.types import (AutoPilotTaskModifier, BrokerNode,
                               ServiceProvider, ServiceProviderNode,
                               SettingsNode)
from trader.const import NEW_YORK_TZ
from trader.enums import MarketSession, OrderAction, PriceType
from trader.models import (Account, AutoPilotTask, ProviderSession, Settings,
                           TradingStrategy)
from trader.providers import get_provider_instance
from trader.utils import get_ask, get_bid, get_limit_price, get_round_price

# pylint: disable=invalid-name
logger = logging.getLogger("trader.api")


def get_autopilot(user_id: int, symbol: str) -> AutoPilotTask:
    return AutoPilotTask.objects.filter(
        user_id=user_id, symbol=symbol, status=AutoPilotTask.RUNNING).first()


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
    INSUFFICIENT_FUNDS = 'INSUFFICIENT_FUNDS'


class BuyStock(relay.ClientIDMutation):
    class Input:
        provider_id = graphene.ID(required=True)
        strategy_id = graphene.ID(required=True)
        symbol = graphene.String(required=True)
        margin = graphene.Decimal()
        price = graphene.Decimal()
        quantity = graphene.Int()
        account_id = graphene.ID()
        autopilot = graphene.Boolean()

    error = graphene.Field(BuyStockError)
    error_message = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, symbol, strategy_id, provider_id,
                               margin='0.00', price='0.0000', quantity=0,
                               account_id=None, autopilot=False):
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

        if not strategy.funded(account):
            return BuyStock(
                error=BuyStockError.INSUFFICIENT_FUNDS,
                error_message='Insufficient funds. Strategy selected ' +
                'requires more cash available for investment.'
            )

        etrade = get_provider_instance(provider)

        if autopilot:
            quote = etrade.get_quote(symbol)
            is_otc = etrade.is_otc(quote)
            user = info.context.user
            settings = Settings.objects.filter(user_id=user.id).first()
            default_modifier = settings.default_autopilot_modifier if settings else None
            discord_webhook = settings.discord_webhook if settings else None
            task = AutoPilotTask(
                signal=AutoPilotTask.BUY,
                user=info.context.user,
                strategy=strategy,
                provider=provider,
                account=account,
                is_otc=is_otc,
                symbol=symbol,
                quantity=quantity,
                entry_price=price,
                base_price=price,
                loss_ref_price=price,
                profit_ref_price=price,
                ref_time=timezone.now(),
                modifier=default_modifier,
                discord_webhook=discord_webhook)
            task.save()
            return BuyStock()

        if Decimal(price):
            limit_price = Decimal(price).quantize(Decimal('0.0001'))
        else:
            quantized_margin = Decimal(margin).quantize(Decimal('0.001'))
            quote = etrade.get_quote(symbol)
            limit_price = get_limit_price(OrderAction.BUY, get_bid(quote),
                                          Decimal(quantized_margin) or strategy.price_margin)

        if not quantity:
            quantity = strategy.get_quantity_for(
                buying_power=account.real_value, price_per_share=limit_price)

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

        # TODO: HANDLE Code: 1527. Message: Opening orders for this security cannot be accepted online at this time. For assistance with placing this order, please contact Customer Service at 1-800-ETRADE-1 (1-800-387-2331).

        return BuyStock()


class SellStockError(graphene.Enum):
    ACCOUNT_NOT_PROVIDED = 'ACCOUNT_NOT_PROVIDED'


class SellStock(relay.ClientIDMutation):
    class Input:
        provider_id = graphene.ID(required=True)
        symbol = graphene.String(required=True)
        margin = graphene.Decimal()
        price = graphene.Decimal()
        quantity = graphene.Int()
        account_id = graphene.ID()

    error = graphene.Field(SellStockError)
    error_message = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, symbol, provider_id,
                               margin='0.00', price='0.0000', quantity=0,
                               account_id=None):
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

        # turn_off_autopilot(info.context.user.id, symbol)
        autopilot = get_autopilot(info.context.user.id, symbol)

        if autopilot:
            autopilot.signal = AutoPilotTask.SELL
            autopilot.save()
            return SellStock()

        etrade = get_provider_instance(provider)

        if Decimal(price):
            limit_price = Decimal(price).quantize(Decimal('0.0001'))
        else:
            quantized_margin = Decimal(margin).quantize(Decimal('0.001'))
            print(f'margin: {Decimal(quantized_margin)}')
            quote = etrade.get_quote(symbol)
            limit_price = get_limit_price(
                OrderAction.SELL, get_ask(quote), margin=Decimal(quantized_margin) or Decimal('0.1'))

        if not quantity:
            quantity = etrade.get_position_quantity(account_key, symbol)

        order_params = {
            'account_key': account_key,
            'market_session': MarketSession.current().value,
            'action': OrderAction.SELL.value,
            'symbol': symbol,
            'price_type': PriceType.LIMIT.value,
            'quantity': quantity,
            'limit_price': limit_price
        }

        preview_ids = etrade.preview_order(
            order_client_id=get_random_string(length=20), **order_params)
        etrade.place_order(order_client_id=get_random_string(
            length=20), preview_ids=preview_ids, **order_params)

        return SellStock()


class StopProfitError(graphene.Enum):
    ACCOUNT_NOT_PROVIDED = 'ACCOUNT_NOT_PROVIDED'
    STRATEGY_NOT_FOUND = 'STRATEGY_NOT_FOUND'
    NOT_ALLOWED_ON_AUTOPILOT = 'NOT_ALLOWED_ON_AUTOPILOT'


class StopProfit(relay.ClientIDMutation):
    class Input:
        provider_id = graphene.ID(required=True)
        symbol = graphene.String(required=True)
        strategy_id = graphene.ID()
        account_id = graphene.ID()

    error = graphene.Field(StopProfitError)
    error_message = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, symbol, provider_id,
                               strategy_id=None, account_id=None):
        account = Account.objects.get(id=account_id) if account_id else None
        provider = ServiceProvider.objects.select_related('session') \
            .get(id=provider_id)

        strategy = None
        if strategy_id:
            strategy = info.context.user.trading_strategies.filter(
                id=strategy_id).first()
            if not strategy:
                return StopProfit(
                    error=StopProfitError.STRATEGY_NOT_FOUND,
                    error_message=f'TradingStrategy with id {strategy_id} not found.'
                )

        account_key = account.account_key.strip() if account \
            else provider.account_key.strip()

        if not account_key:
            return StopProfit(
                error=StopProfitError.ACCOUNT_NOT_PROVIDED,
                error_message='Either specify an accountId that has a valid accountKey ' +
                'or configure a default accountKey on the provider.'
            )

        autopilot = get_autopilot(info.context.user.id, symbol)
        if autopilot:
            return StopProfit(
                error=StopProfitError.NOT_ALLOWED_ON_AUTOPILOT,
                error_message='You must turn off autopilot first.'
            )

        etrade = get_provider_instance(provider)
        position_quantity, entry_price = etrade.get_position(
            account_key, symbol)

        if strategy:
            profit_amount = entry_price * (strategy.profit_percent / 100)
            stop_price = get_round_price(entry_price + profit_amount)
        else:
            quote = etrade.get_quote(symbol)
            last_price = get_ask(quote)
            profit_amount = last_price * Decimal('0.02')
            stop_price = get_round_price(last_price + profit_amount)

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

        return StopProfit()


class StopLossError(graphene.Enum):
    ACCOUNT_NOT_PROVIDED = 'ACCOUNT_NOT_PROVIDED'
    NOT_ALLOWED_ON_AUTOPILOT = 'NOT_ALLOWED_ON_AUTOPILOT'


class StopLoss(relay.ClientIDMutation):
    class Input:
        provider_id = graphene.ID(required=True)
        symbol = graphene.String(required=True)
        account_id = graphene.ID()

    error = graphene.Field(StopLossError)
    error_message = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, symbol, provider_id, account_id=None):
        account = Account.objects.get(id=account_id) if account_id else None
        provider = ServiceProvider.objects.select_related('session') \
            .get(id=provider_id)
        account_key = account.account_key.strip() if account \
            else provider.account_key.strip()

        if not account_key:
            return StopLoss(
                error=StopLossError.ACCOUNT_NOT_PROVIDED,
                error_message='Either specify an accountId that has a valid accountKey ' +
                'or configure a default accountKey on the provider.'
            )

        autopilot = get_autopilot(info.context.user.id, symbol)
        if autopilot:
            return StopLoss(
                error=StopLossError.NOT_ALLOWED_ON_AUTOPILOT,
                error_message='You must turn off autopilot first.'
            )

        etrade = get_provider_instance(provider)
        position_quantity = etrade.get_position_quantity(account_key, symbol)
        quote = etrade.get_quote(symbol)
        last_price = get_bid(quote)
        stop_price = get_round_price(
            last_price - (last_price * Decimal('0.02')))
        limit_price = get_limit_price(
            OrderAction.SELL, stop_price, margin=Decimal('0.02'))

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

        return StopLoss()


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
    ALREADY_EXISTS = 'ALREADY_EXISTS'
    NO_POSITION_FOR_SYMBOL = 'NO_POSITION_FOR_SYMBOL'


class AutoPilotON(relay.ClientIDMutation):
    _settings = None

    class Input:
        symbol = graphene.String(required=True)
        strategy_id = graphene.ID()
        provider_id = graphene.ID()
        account_id = graphene.ID()
        modifier = graphene.Field(AutoPilotTaskModifier)

    error = graphene.Field(AutoPilotONError)
    error_message = graphene.String()

    @classmethod
    def _get_settings(cls, info):
        if not cls._settings:
            settings = Settings.objects.filter(user_id=info.context.user.id) \
                .select_related('default_strategy', 'default_broker__default_provider') \
                .first()
            cls._settings = settings
        return cls._settings

    @classmethod
    def get_default_modifier(cls, info):
        settings = cls._get_settings(info)
        if not settings:
            return None
        return settings.default_autopilot_modifier

    @classmethod
    def get_discord_webhook(cls, info):
        settings = cls._get_settings(info)
        if not settings:
            return None
        return settings.discord_webhook

    @classmethod
    def get_default_strategy(cls, info):
        settings = cls._get_settings(info)
        if not settings:
            return None
        return settings.default_strategy

    @classmethod
    def get_default_provider(cls, info):
        settings = cls._get_settings(info)
        if not settings:
            return None
        return settings.default_broker.default_provider

    @classmethod
    def get_default_account(cls, info):
        settings = cls._get_settings(info)
        if not settings:
            return None
        default_provider = cls.get_default_provider(info)
        if not default_provider:
            return None
        return Account.objects.get(account_key=default_provider.account_key)

    @classmethod
    def mutate_and_get_payload(cls, root, info, symbol, strategy_id=None,
                               provider_id=None, account_id=None,
                               modifier=None):
        user = info.context.user

        strategy = user.trading_strategies.get(
            id=strategy_id) if strategy_id else cls.get_default_strategy(info)
        if not strategy:
            return AutoPilotON(error=AutoPilotONError.STRATEGY_REQUIRED,
                               error_message='Either set the strategy_id param or configure a default.')

        provider = user.service_providers.get(
            id=provider_id) if provider_id else cls.get_default_privider(info)
        if not provider:
            return AutoPilotON(error=AutoPilotONError.PROVIDER_REQUIRED,
                               error_message='Either set the provider_id param or configure a default.')

        account = user.accounts.get(
            id=account_id) if account_id else cls.get_default_account(info)
        if not account:
            return AutoPilotON(error=AutoPilotONError.ACCOUNT_REQUIRED,
                               error_message='Either set the account_id param or configure a default.')

        if AutoPilotTask.objects.filter(symbol=symbol, status=AutoPilotTask.RUNNING).exists():
            return AutoPilotON(error=AutoPilotONError.ALREADY_EXISTS,
                               error_message=f'Autopilot for {symbol} already exists.')

        if modifier is None:
            modifier = cls.get_default_modifier(user)

        discord_webhook = cls.get_discord_webhook(info)

        etrade = get_provider_instance(provider)
        quantity, entry_price = etrade.get_position(
            account.account_key, symbol)
        if not quantity or not entry_price:
            return AutoPilotON(error=AutoPilotONError.NO_POSITION_FOR_SYMBOL,
                               error_message=f'No position found for {symbol}. Position: {quantity}@{entry_price}')

        quote = etrade.get_quote(symbol)
        is_otc = etrade.is_otc(quote)

        task = AutoPilotTask(
            user=user,
            strategy=strategy,
            provider=provider,
            account=account,
            is_otc=is_otc,
            symbol=symbol,
            quantity=quantity,
            entry_price=entry_price,
            base_price=entry_price,
            loss_ref_price=entry_price,
            profit_ref_price=entry_price,
            ref_time=timezone.now(),
            modifier=modifier,
            discord_webhook=discord_webhook)

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
    stop_loss = StopLoss.Field(required=True)
    stop_profit = StopProfit.Field(required=True)
    cancel_order = CancelOrder.Field(required=True)
    save_settings = SaveSettings.Field(required=True)
    auto_pilot_ON = AutoPilotON.Field(required=True)
    auto_pilot_OFF = AutoPilotOFF.Field(required=True)
