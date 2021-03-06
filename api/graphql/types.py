import datetime
from decimal import Decimal

import graphene
from graphene import relay
from graphene_django.types import DjangoObjectType

from trader.models import (Account, AutoPilotTask, Broker, BufferCash,
                           ProviderSession, ServiceProvider, Settings,
                           TradingStrategy)
from trader.providers import get_provider_instance
from trader.utils import get_ask, get_bid, get_last, get_volume

from .graphene_overrides import NonNullConnection


class DatabaseId(graphene.Interface):
    database_id = graphene.Int(required=True)

    def resolve_database_id(self, info, **kwargs):
        return getattr(self, 'id')


class SettingsNode(DjangoObjectType):
    class Meta:
        # removing user from excluded fields due to following warning:
        # UserWarning: Field name "user" matches an attribute on Django model
        # "trader.Settings" but it's not a model field so Graphene cannot
        # determine what type it should be. Either define the type of the field
        # on DjangoObjectType "SettingsNode" or remove it from the "fields" list.
        # exclude_fields = ('user',)
        model = Settings
        interfaces = (relay.Node, DatabaseId)

    @classmethod
    # pylint: disable=redefined-builtin
    def get_node(cls, info, id):
        return Settings.objects.get(id=id)


class TradingStrategyNode(DjangoObjectType):
    class Meta:
        # removing user from excluded fields due to following warning:
        # UserWarning: Field name "user" matches an attribute on Django model
        # "trader.TradingStrategy" but it's not a model field so Graphene cannot
        # determine what type it should be. Either define the type of the field
        # on DjangoObjectType "TradingStrategyNode" or remove it from the "fields" list.
        # exclude_fields = ('user',)
        model = TradingStrategy
        interfaces = (relay.Node, DatabaseId)

    @classmethod
    # pylint: disable=redefined-builtin
    def get_node(cls, info, id):
        return TradingStrategy.objects.get(id=id)


class SessionStatus(graphene.Enum):
    REQUESTING = ProviderSession.REQUESTING
    CONNECTED = ProviderSession.CONNECTED
    INACTIVE = ProviderSession.INACTIVE
    EXPIRED = ProviderSession.EXPIRED
    CLOSED = ProviderSession.CLOSED


class ProviderSessionNode(DjangoObjectType):
    status = graphene.Field(SessionStatus)

    class Meta:
        # exclude_fields = ('provider',)
        model = ProviderSession
        interfaces = (relay.Node, DatabaseId)

    @classmethod
    # pylint: disable=redefined-builtin
    def get_node(cls, info, id):
        return ProviderSession.objects.get(id=id)


class ServiceProviderNode(DjangoObjectType):
    session = graphene.Field(ProviderSessionNode)
    quote = graphene.Field(lambda: QuoteType, symbol=graphene.String())
    broker = graphene.Field(lambda: BrokerNode, required=True)
    session_status = graphene.Field(SessionStatus, required=True)

    class Meta:
        # removing user from excluded fields due to following warning:
        # UserWarning: Field name "user" matches an attribute on Django model
        # "trader.ServiceProvider" but it's not a model field so Graphene cannot
        # determine what type it should be. Either define the type of the field
        # on DjangoObjectType "ServiceProviderNode" or remove it from the "fields" list.
        # exclude_fields = ('user',)
        model = ServiceProvider
        interfaces = (relay.Node, DatabaseId)

    @classmethod
    # pylint: disable=redefined-builtin
    def get_node(cls, info, id):
        return info.context.user.service_providers.get(id=id)

    def resolve_session_status(self, *args, **kwargs):
        session = ProviderSession.objects.filter(provider=self).first()
        if not session:
            return ProviderSession.CLOSED

        etrade = get_provider_instance(self)
        if self.session and not etrade.is_session_active():
            self.session.delete()
            self.session = None
            self.save()
            return ProviderSession.CLOSED

        return self.session.status

    def resolve_quote(self, info, symbol):
        etrade = get_provider_instance(self)
        quote_data = etrade.get_quote(symbol)

        if not quote_data:
            return None

        return QuoteType(
            volume=get_volume(quote_data),
            last=get_last(quote_data),
            bid=get_bid(quote_data),
            ask=get_ask(quote_data),
            last_trade_direction=Decimal(
                str(quote_data.get('All').get('dirLast'))),
            market_cap=Decimal(str(quote_data.get('All').get('marketCap'))),
            shares_outstanding=quote_data.get('All').get('sharesOutstanding'),
            primary_exchange=quote_data.get('All').get('primaryExchange'),
            company_name=quote_data.get('All').get('companyName'),
        )


class ServiceProviderConnection(NonNullConnection):
    class Meta:
        node = ServiceProviderNode

    # class ServiceProviderEdge(graphene.ObjectType):
    #     node = graphene.Field(ServiceProviderNode, required=True)
    #     cursor = graphene.String(required=True)

    # edges = graphene.List(graphene.NonNull(ServiceProviderEdge), required=True)


class BufferCashNode(DjangoObjectType):
    class Meta:
        model = BufferCash
        interfaces = (relay.Node, DatabaseId)

    @classmethod
    # pylint: disable=redefined-builtin
    def get_node(cls, info, id):
        return BufferCash.objects.get(id=id)


class AccountNode(DjangoObjectType):
    buffer_cash = graphene.Field(BufferCashNode)
    real_value = graphene.Float(required=True)

    class Meta:
        model = Account
        interfaces = (relay.Node, DatabaseId)

    @classmethod
    # pylint: disable=redefined-builtin
    def get_node(cls, info, id):
        return Account.objects.get(id=id)

    def resolve_buffer_cash(self, info, **kwargs):
        return BufferCash.objects.filter(account_id=self.id).first()

    def resolve_real_value(self, info, **kwargs):
        return self.real_value


class AccountConnection(NonNullConnection):
    class Meta:
        node = AccountNode


class BrokerNode(DjangoObjectType):
    service_providers = relay.ConnectionField(
        ServiceProviderConnection, required=True)
    service_provider = graphene.Field(
        ServiceProviderNode, database_id=graphene.ID(), slug=graphene.String())
    accounts = relay.ConnectionField(AccountConnection, required=True)

    class Meta:
        # removing user from excluded fields due to following warning:
        # UserWarning: Field name "user" matches an attribute on Django model
        # "trader.AutoPilotTask" but it's not a model field so Graphene cannot
        # determine what type it should be. Either define the type of the field
        # on DjangoObjectType "AutoPilotTaskNode" or remove it from the "fields" list.
        # exclude_fields = ('user',)
        model = Broker
        interfaces = (relay.Node, DatabaseId)

    @classmethod
    # pylint: disable=redefined-builtin
    def get_node(cls, info, id):
        return info.context.user.brokers.get(id=id)

    def resolve_service_provider(self, info, **kwargs):
        database_id = kwargs.get('database_id', None)
        slug = kwargs.get('slug', None)
        if database_id:
            return self.service_providers.get(id=database_id)
        if slug:
            return self.service_providers.get(slug=slug)
        return None

    def resolve_service_providers(self, info, **kwargs):
        return self.service_providers.all()

    def resolve_accounts(self, info, **kwargs):
        return self.accounts.all()


class BrokerConnection(NonNullConnection):
    class Meta:
        node = BrokerNode


class AutoPilotTaskStatus(graphene.Enum):
    READY = AutoPilotTask.READY  # default
    QUEUED = AutoPilotTask.QUEUED
    RUNNING = AutoPilotTask.RUNNING
    DONE = AutoPilotTask.DONE
    PAUSED = AutoPilotTask.PAUSED


class AutoPilotTaskState(graphene.Enum):
    BUYING = AutoPilotTask.BUYING
    WATCHING = AutoPilotTask.WATCHING  # default
    SELLING = AutoPilotTask.SELLING
    ERROR = AutoPilotTask.ERROR


class AutoPilotTaskModifier(graphene.Enum):
    FOLLOW_STRATEGY = AutoPilotTask.FOLLOW_STRATEGY  # default
    MAXIMIZE_PROFIT = AutoPilotTask.MAXIMIZE_PROFIT
    MINIMIZE_LOSS = AutoPilotTask.MINIMIZE_LOSS
    MIN_LOSS_MAX_PROFIT = AutoPilotTask.MIN_LOSS_MAX_PROFIT


class AutoPilotTaskNode(DjangoObjectType):
    status = graphene.Field(AutoPilotTaskStatus, required=True)
    state = graphene.Field(AutoPilotTaskState, required=True)
    modifier = graphene.Field(AutoPilotTaskModifier, required=True)

    class Meta:
        # removing user from excluded fields due to following warning:
        # UserWarning: Field name "user" matches an attribute on Django model
        # "trader.AutoPilotTask" but it's not a model field so Graphene cannot
        # determine what type it should be. Either define the type of the field
        # on DjangoObjectType "AutoPilotTaskNode" or remove it from the "fields" list.
        # exclude_fields = ('user',)
        model = AutoPilotTask
        interfaces = (relay.Node, DatabaseId)

    @classmethod
    # pylint: disable=redefined-builtin
    def get_node(cls, info, id):
        return AutoPilotTask.objects.get(id=id, user_id=info.context.user.id)


class AutoPilotTaskConnection(NonNullConnection):
    class Meta:
        node = AutoPilotTaskNode


class QuoteType(graphene.ObjectType):
    volume = graphene.Int()
    last = graphene.Decimal()
    bid = graphene.Decimal()
    ask = graphene.Decimal()
    last_trade_direction = graphene.Decimal()
    market_cap = graphene.Decimal()
    shares_outstanding = graphene.Int()
    primary_exchange = graphene.String()
    company_name = graphene.String()


class OrderType(graphene.ObjectType):
    order_id = graphene.ID(required=True)
    symbol = graphene.String(required=True)
    price_type = graphene.String(required=True)
    pending_quantity = graphene.Int(required=True)
    ordered_quantity = graphene.Int(required=True)
    filled_quantity = graphene.Int(required=True)
    limit_price = graphene.Decimal(required=True)
    stop_price = graphene.Decimal()
    stop_limit_price = graphene.Decimal()
    execution_price = graphene.Decimal(required=True)
    status = graphene.String(required=True)
    action = graphene.String(required=True)

    def resolve_order_id(self, info, **kwargs):
        order_id = self.get("orderId")
        if not order_id:
            raise ValueError(
                f'Expecting a value for order_id. Got: "{order_id}"')
        return order_id

    def resolve_symbol(self, info, **kwargs):
        details = self.get("OrderDetail")[0]
        instrument = details.get("Instrument")[0]
        symbol = instrument.get("Product").get("symbol")
        if not symbol:
            raise ValueError(f'Expecting a value for symbol. Got: "{symbol}"')
        return instrument.get("Product").get("symbol")

    def resolve_stop_price(self, info, **kwargs):
        details = self.get("OrderDetail")[0]
        stop_price = details.get("stopPrice")
        if not stop_price and stop_price != 0:
            return None
        value = Decimal(str(stop_price))
        if value.adjusted() > 0:
            return value.quantize(Decimal('0.01'))
        return value

    def resolve_stop_limit_price(self, info, **kwargs):
        details = self.get("OrderDetail")[0]
        stop_limit_price = details.get("stopLimitPrice")
        if not stop_limit_price and stop_limit_price != 0:
            return None
        value = Decimal(str(stop_limit_price))
        if value.adjusted() > 0:
            return value.quantize(Decimal('0.01'))
        return value

    def resolve_pending_quantity(self, info, **kwargs):
        details = self.get("OrderDetail")[0]
        instrument = details.get("Instrument")[0]
        ordered_quantity = instrument.get("orderedQuantity")
        filled_quantity = instrument.get("filledQuantity")
        if not ordered_quantity and ordered_quantity != 0:
            raise ValueError(
                f'pendingQuantity: Expecting a value for orderedQuantity. Got: "{ordered_quantity}"')
        if not filled_quantity and filled_quantity != 0:
            raise ValueError(
                f'pendingQuantity: Expecting a value for filledQuantity. Got: "{filled_quantity}"')
        return int(ordered_quantity) - int(filled_quantity)

    def resolve_ordered_quantity(self, info, **kwargs):
        details = self.get("OrderDetail")[0]
        instrument = details.get("Instrument")[0]
        quantity = instrument.get("orderedQuantity")
        if not quantity and quantity != 0:
            raise ValueError(
                f'Expecting a value for orderedQuantity. Got: "{quantity}"')
        return int(quantity)

    def resolve_filled_quantity(self, info, **kwargs):
        details = self.get("OrderDetail")[0]
        instrument = details.get("Instrument")[0]
        quantity = instrument.get("filledQuantity")
        if not quantity and quantity != 0:
            raise ValueError(
                f'Expecting a value for filledQuantity. Got: "{quantity}"')
        return int(quantity)

    def resolve_limit_price(self, info, **kwargs):
        details = self.get("OrderDetail")[0]
        limit_price = details.get("limitPrice")
        if not limit_price and limit_price != 0:
            raise ValueError(
                f'Expecting a value for limit_price. Got: "{limit_price}"')
        value = Decimal(str(limit_price))
        # if value.adjusted() > 0:
        #     return value.quantize(Decimal('0.01'))
        return value

    def resolve_execution_price(self, info, **kwargs):
        details = self.get("OrderDetail")[0]
        instrument = details.get("Instrument")[0]
        execution_price = instrument.get("averageExecutionPrice", 0)
        value = Decimal(str(execution_price))
        # if value.adjusted() > 0:
        #     return value.quantize(Decimal('0.01'))
        return value

    def resolve_status(self, info, **kwargs):
        details = self.get("OrderDetail")[0]
        status = details.get("status")
        if not status:
            raise ValueError(
                f'Expecting a value for status. Got: "{status}"')
        return status

    def resolve_action(self, info, **kwargs):
        details = self.get("OrderDetail")[0]
        instrument = details.get("Instrument")[0]
        action = instrument.get("orderAction")
        if not action:
            raise ValueError(
                f'Expecting a value for action. Got: "{action}"')
        return action


class TransactionType(graphene.ObjectType):
    symbol = graphene.String(required=True)
    transaction_type = graphene.String(required=True)
    quantity = graphene.Int(required=True)
    amount = graphene.Decimal(required=True)
    price = graphene.Decimal(required=True)
    fee = graphene.Decimal(required=True)
    transaction_date = graphene.DateTime(required=True)

    def resolve_symbol(self, info, **kwargs):
        brokerage = self.get("brokerage")
        product = brokerage.get("product")
        symbol = product.get("symbol")
        if not symbol:
            raise ValueError(
                f'Expecting a value for symbol. Got: "{symbol}"')
        return symbol

    def resolve_transaction_type(self, info, **kwargs):
        transaction_type = self.get("transactionType")
        if not transaction_type:
            raise ValueError(
                f'Expecting a value for transaction_type. Got: "{transaction_type}"')
        return transaction_type

    def resolve_quantity(self, info, **kwargs):
        brokerage = self.get("brokerage")
        quantity = brokerage.get("quantity")
        if not quantity:
            raise ValueError(
                f'Expecting a value for quantity. Got: "{quantity}"')
        return quantity

    def resolve_amount(self, info, **kwargs):
        amount = self.get("amount")
        if not amount:
            raise ValueError(
                f'Expecting a value for amount. Got: "{amount}"')
        return amount

    def resolve_price(self, info, **kwargs):
        brokerage = self.get("brokerage")
        price = brokerage.get("price")
        if not price:
            raise ValueError(
                f'Expecting a value for price. Got: "{price}"')
        return price

    def resolve_fee(self, info, **kwargs):
        brokerage = self.get("brokerage")
        fee = brokerage.get("fee")
        if not fee:
            raise ValueError(
                f'Expecting a value for fee. Got: "{fee}"')
        return fee

    def resolve_transaction_date(self, info, **kwargs):
        transaction_date = datetime.datetime.fromtimestamp(
            self.get("transactionDate")/1000)
        if not transaction_date:
            raise ValueError(
                f'Expecting a value for transaction_date. Got: "{transaction_date}"')
        return transaction_date


class PerformanceType(graphene.ObjectType):
    symbol = graphene.String(required=True)
    quantity = graphene.Int(required=True)
    amount = graphene.Decimal(required=True)
    date = graphene.DateTime(required=True)

    def resolve_amount(self, info, **kwargs):
        return self.get('amount').quantize(Decimal('0.01'))

    def resolve_quantity(self, info, **kwargs):
        return self.get('bought')


class PositionType(graphene.ObjectType):
    symbol = graphene.String(required=True)
    entry_price = graphene.Decimal(required=True)
    price_paid = graphene.Decimal(required=True)
    quantity = graphene.Int(required=True)
    total_gain = graphene.Decimal(required=True)
    total_gain_pct = graphene.Decimal(required=True)
    autopilot = graphene.Field(AutoPilotTaskNode)

    def resolve_symbol(self, info, **kwargs):
        symbol = self.get("symbolDescription")
        if not symbol:
            raise ValueError(
                f'Expecting a value for symbol. Got: "{symbol}"')
        return symbol

    def resolve_entry_price(self, info, **kwargs):
        price = self.get("price")
        if price is None:
            raise ValueError(
                f'Expecting a value for entry_price. Got: "{price}"')
        value = Decimal(str(price))
        if value.adjusted() >= 0:
            return value.quantize(Decimal('0.01'))
        return value

    def resolve_price_paid(self, info, **kwargs):
        price_paid = self.get("pricePaid")
        if price_paid is None:
            raise ValueError(
                f'Expecting a value for price_paid. Got: "{price_paid}"')
        value = Decimal(str(price_paid))
        if value.adjusted() >= 0:
            return value.quantize(Decimal('0.01'))
        return value

    def resolve_quantity(self, info, **kwargs):
        quantity = self.get("quantity")
        if quantity is None:
            raise ValueError(
                f'Expecting a value for quantity. Got: "{quantity}"')
        return quantity

    def resolve_total_gain(self, info, **kwargs):
        total_gain = self.get("totalGain")
        if total_gain is None:
            raise ValueError(
                f'Expecting a value for total_gain. Got: "{total_gain}"')
        return Decimal(str(total_gain)).quantize(Decimal('0.01'))

    def resolve_total_gain_pct(self, info, **kwargs):
        total_gain_pct = self.get("totalGainPct")
        if total_gain_pct is None:
            raise ValueError(
                f'Expecting a value for total_gain_pct. Got: "{total_gain_pct}"')
        return Decimal(str(total_gain_pct)).quantize(Decimal('0.01'))

    def resolve_autopilot(self, info, **kwargs):
        symbol = self.get("symbolDescription")
        if not symbol:
            raise ValueError(
                f'Expecting a value for symbol. Got: "{symbol}"')

        return AutoPilotTask.objects.filter(
            symbol=symbol, status=AutoPilotTask.RUNNING, user_id=info.context.user.id) \
            .order_by('-id').first()


class ViewerCredentialsType(graphene.ObjectType):
    database_id = graphene.Int(required=True)
    full_name = graphene.String(required=True)

    def resolve_database_id(self, info, **kwargs):
        return info.context.user.id

    def resolve_full_name(self, info, **kwargs):
        user = info.context.user
        return f'{user.first_name} {user.last_name}'.strip() or user.username


class ServiceProviderSlugInput(graphene.InputObjectType):
    broker_slug = graphene.String(required=True)
    priverder_slug = graphene.String(required=True)


class ViewerType(graphene.ObjectType):
    credentials = graphene.Field(ViewerCredentialsType, required=True)
    settings = graphene.Field(SettingsNode)
    trading_strategies = graphene.List(
        graphene.NonNull(TradingStrategyNode), required=True)
    brokers = graphene.List(graphene.NonNull(BrokerNode), required=True)
    broker = graphene.Field(
        BrokerNode, database_id=graphene.ID(), slug=graphene.String())
    service_providers = graphene.List(
        graphene.NonNull(ServiceProviderNode), required=True)
    service_provider = graphene.Field(
        ServiceProviderNode, database_id=graphene.ID(), slug=ServiceProviderSlugInput())
    accounts = graphene.List(graphene.NonNull(AccountNode), required=True)
    orders = graphene.List(
        graphene.NonNull(OrderType), required=True, provider_id=graphene.ID(required=True), account_id=graphene.ID())
    positions = graphene.List(
        graphene.NonNull(PositionType), required=True, provider_id=graphene.ID(required=True), account_id=graphene.ID())
    transactions = graphene.List(
        graphene.NonNull(TransactionType), required=True,
        provider_id=graphene.ID(required=True), account_id=graphene.ID())
    performances = graphene.List(
        graphene.NonNull(PerformanceType), required=True,
        provider_id=graphene.ID(required=True), account_id=graphene.ID())

    def resolve_credentials(self, info, **kwargs):
        return ViewerCredentialsType()

    def resolve_settings(self, info, **kwargs):
        return Settings.objects.filter(user=info.context.user).first()

    def resolve_trading_strategies(self, info, **kwargs):
        return info.context.user.trading_strategies.all()

    def resolve_brokers(self, info, **kwargs):
        return info.context.user.brokers.all()

    def resolve_broker(self, info, **kwargs):
        database_id = kwargs.get('database_id', None)
        slug = kwargs.get('slug', None)
        if database_id:
            return info.context.user.brokers.get(id=database_id)
        if slug:
            return info.context.user.brokers.get(slug=slug)
        return None

    def resolve_service_providers(self, info, **kwargs):
        return info.context.user.service_providers.all()

    def resolve_service_provider(self, info, **kwargs):
        database_id = kwargs.get('database_id', None)
        slug = kwargs.get('slug', None)
        if database_id:
            return info.context.user.service_providers.get(id=database_id)
        if slug:
            broker_slug = slug.get('broker_slug')
            provider_slug = slug.get('provider_slug')
            broker = info.context.user.brokers.get(slug=broker_slug)
            return broker.service_providers.get(slug=provider_slug)
        return None

    def resolve_accounts(self, info, **kwargs):
        return info.context.user.accounts.all()

    def resolve_orders(self, info, provider_id, account_id=None, **kwargs):
        provider = info.context.user.service_providers.get(id=provider_id)
        account = info.context.user.accounts.get(
            id=account_id) if account_id else None
        account_key = account.account_key.strip() if account \
            else provider.account_key.strip()

        if not account_key:
            raise AttributeError(
                'Account Key not provided. ' +
                'Either specify accountId argument or configure a default accountKey on the provider.'
            )

        etrade = get_provider_instance(provider)
        return etrade.get_orders(account_key) or []

    def resolve_positions(self, info, provider_id, account_id=None, **kwargs):
        provider = info.context.user.service_providers.get(id=provider_id)
        account = info.context.user.accounts.get(
            id=account_id) if account_id else None
        account_key = account.account_key.strip() if account \
            else provider.account_key.strip()

        if not account_key:
            raise AttributeError(
                'Account Key not provided. ' +
                'Either specify accountId argument or configure a default accountKey on the provider.'
            )

        etrade = get_provider_instance(provider)
        return etrade.get_positions(account_key) or []

    def resolve_transactions(self, info, provider_id, account_id=None, **kwargs):
        provider = info.context.user.service_providers.get(id=provider_id)
        account = info.context.user.accounts.get(
            id=account_id) if account_id else None
        account_key = account.account_key.strip() if account \
            else provider.account_key.strip()

        if not account_key:
            raise AttributeError(
                'Account Key not provided. ' +
                'Either specify accountId argument or configure a default accountKey on the provider.'
            )

        etrade = get_provider_instance(provider)
        return etrade.get_transactions(account_key) or []

    def resolve_performances(self, info, provider_id, account_id=None, **kwargs):
        provider = info.context.user.service_providers.get(id=provider_id)
        account = info.context.user.accounts.get(
            id=account_id) if account_id else None
        account_key = account.account_key.strip() if account \
            else provider.account_key.strip()

        if not account_key:
            raise AttributeError(
                'Account Key not provided. ' +
                'Either specify accountId argument or configure a default accountKey on the provider.'
            )

        etrade = get_provider_instance(provider)
        transactions = etrade.get_transactions(account_key) or []

        symbol_map = {}
        for tran in transactions:
            brokerage = tran.get("brokerage")
            product = brokerage.get("product")
            transaction_type = tran.get("transactionType")
            transaction_date = tran.get("transactionDate")
            symbol = product.get("symbol")
            quantity = brokerage.get("quantity")
            amount = tran.get("amount")
            if transaction_type not in ('Bought', 'Sold'):
                continue
            if symbol not in symbol_map:
                performance = {
                    'symbol': symbol,
                    'amount': Decimal(amount),
                    'date': datetime.datetime.fromtimestamp(transaction_date/1000),
                    'bought': int(quantity) if transaction_type == 'Bought' else 0,
                    'sold': int(quantity) * -1 if transaction_type == 'Sold' else 0
                }
                symbol_map[symbol] = performance
            else:
                performace = symbol_map[symbol]
                performace['date'] = datetime.datetime.fromtimestamp(
                    transaction_date/1000)
                performace['amount'] = performace['amount'] + \
                    Decimal(amount)
                if transaction_type == 'Bought':
                    performace['bought'] = performace['bought'] + \
                        int(quantity)
                else:
                    performace['sold'] = performace['sold'] + \
                        int(quantity) * -1

        performances = [val for val in symbol_map.values()
                        if val['bought'] == val['sold']]
        performances.sort(key=lambda val: val['date'], reverse=True)

        return performances


class Query(graphene.ObjectType):
    node = relay.Node.Field()
    viewer = graphene.Field(ViewerType, required=True)

    def resolve_viewer(self, info, **kwargs):
        return ViewerType()
