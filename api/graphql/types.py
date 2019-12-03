import graphene
from graphene import relay
from graphene_django.types import DjangoObjectType

from trader.models import (Account, Broker, ProviderSession, ServiceProvider,
                           TradingStrategy)
from trader.providers import Etrade


class DatabaseId(graphene.Interface):
    database_id = graphene.Int()

    def resolve_database_id(self, info, **kwargs):
        return getattr(self, 'id')


class TradingStrategyNode(DjangoObjectType):
    class Meta:
        exclude_fields = ('user',)
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
        exclude_fields = ('provider',)
        model = ProviderSession
        interfaces = (relay.Node, DatabaseId)

    @classmethod
    # pylint: disable=redefined-builtin
    def get_node(cls, info, id):
        return ProviderSession.objects.get(id=id)


class QuoteType(graphene.ObjectType):
    volume = graphene.Int()
    last_trade = graphene.Float()
    last_trade_direction = graphene.Float()
    market_cap = graphene.Float()
    shares_outstanding = graphene.Int()
    primary_exchange = graphene.String()
    company_name = graphene.String()


class ServiceProviderNode(DjangoObjectType):
    session = graphene.Field(ProviderSessionNode)
    quote = graphene.Field(QuoteType, symbol=graphene.String())

    class Meta:
        exclude_fields = ('user', 'broker')
        model = ServiceProvider
        interfaces = (relay.Node, DatabaseId)

    @classmethod
    # pylint: disable=redefined-builtin
    def get_node(cls, info, id):
        return info.context.user.service_providers.get(id=id)

    def resolve_quote(self, info, symbol):
        etrade = Etrade(self)
        quote_data = etrade.get_quote(symbol)

        if not quote_data:
            return None

        return QuoteType(
            volume=quote_data.get('All').get('totalVolume'),
            last_trade=quote_data.get('All').get('lastTrade'),
            last_trade_direction=quote_data.get('All').get('dirLast'),
            market_cap=quote_data.get('All').get('marketCap'),
            shares_outstanding=quote_data.get('All').get('sharesOutstanding'),
            primary_exchange=quote_data.get('All').get('primaryExchange'),
            company_name=quote_data.get('All').get('companyName'),
        )


class BrokerNode(DjangoObjectType):
    class Meta:
        exclude_fields = ('user',)
        model = Broker
        interfaces = (relay.Node, DatabaseId)

    @classmethod
    # pylint: disable=redefined-builtin
    def get_node(cls, info, id):
        return info.context.user.brokers.get(id=id)


class AccountNode(DjangoObjectType):
    class Meta:
        model = Account
        interfaces = (relay.Node, DatabaseId)

    @classmethod
    # pylint: disable=redefined-builtin
    def get_node(cls, info, id):
        return Account.objects.get(id=id)


class PositionType(graphene.ObjectType):
    pass


class OrderType(graphene.ObjectType):
    order_id = graphene.ID()
    symbol = graphene.String()
    quantity = graphene.Int()
    limit_price = graphene.Float()
    status = graphene.String()

    def resolve_order_id(self, info, **kwargs):
        return self.get("orderId")

    def resolve_symbol(self, info, **kwargs):
        details = self.get("OrderDetail")[0]
        instrument = details.get("Instrument")[0]
        return instrument.get("Product").get("symbol")

    def resolve_quantity(self, info, **kwargs):
        details = self.get("OrderDetail")[0]
        instrument = details.get("Instrument")[0]
        return instrument.get("quantity")

    def resolve_limit_price(self, info, **kwargs):
        details = self.get("OrderDetail")[0]
        return details.get("limitPrice")

    def resolve_status(self, info, **kwargs):
        details = self.get("OrderDetail")[0]
        return details.get("status")


class ViewerCredentialsType(graphene.ObjectType):
    database_id = graphene.Int()
    full_name = graphene.String()

    def resolve_database_id(self, info, **kwargs):
        return info.context.user.id

    def resolve_full_name(self, info, **kwargs):
        user = info.context.user
        return f'{user.first_name} {user.last_name}'.strip() or user.username


class ViewerType(graphene.ObjectType):
    credentials = graphene.Field(ViewerCredentialsType)
    trading_strategies = graphene.List(TradingStrategyNode)
    brokers = graphene.List(BrokerNode)
    accounts = graphene.List(AccountNode)
    # positions = graphene.List(PositionType)
    orders = graphene.List(
        OrderType, provider_id=graphene.ID(), account_id=graphene.ID())

    def resolve_credentials(self, info, **kwargs):
        return ViewerCredentialsType()

    def resolve_trading_strategies(self, info, **kwargs):
        return info.context.user.trading_strategies.all()

    def resolve_brokers(self, info, **kwargs):
        return info.context.user.brokers.all()

    def resolve_accounts(self, info, **kwargs):
        return info.context.user.accounts.all()

    def resolve_prositions(self, info, **kwargs):
        return info.context.user.positions.all()

    def resolve_orders(self, info, provider_id, account_id, **kwargs):
        provider = info.context.user.providers.get(id=provider_id)
        account = info.context.user.get(id=account_id)

        etrade = Etrade(provider)
        return etrade.get_orders(account.account_key)


class Query(graphene.ObjectType):
    node = relay.Node.Field()
    viewer = graphene.Field(ViewerType)

    def resolve_viewer(self, info, **kwargs):
        return ViewerType()
