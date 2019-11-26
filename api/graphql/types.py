import graphene
from graphene import relay
from graphene_django.types import DjangoObjectType

from trader.models import (Account, Broker, Order, Position, ProviderSession,
                           ServiceProvider, TradingStrategy)
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
        return ServiceProvider.objects.get(id=id)

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
        return Broker.objects.get(id=id)


class AccountNode(DjangoObjectType):
    class Meta:
        model = Account
        interfaces = (relay.Node, DatabaseId)

    @classmethod
    # pylint: disable=redefined-builtin
    def get_node(cls, info, id):
        return Account.objects.get(id=id)


class PositionNode(DjangoObjectType):
    class Meta:
        model = Position
        interfaces = (relay.Node, DatabaseId)

    @classmethod
    # pylint: disable=redefined-builtin
    def get_node(cls, info, id):
        return Position.objects.get(id=id)


class OrderNode(DjangoObjectType):
    class Meta:
        model = Order
        interfaces = (relay.Node, DatabaseId)

    @classmethod
    # pylint: disable=redefined-builtin
    def get_node(cls, info, id):
        return Order.objects.get(id=id)


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
    positions = graphene.List(PositionNode)
    orders = graphene.List(OrderNode)

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

    def resolve_orders(self, info, **kwargs):
        return info.context.user.orders.all()


class Query(graphene.ObjectType):
    node = relay.Node.Field()
    viewer = graphene.Field(ViewerType)

    def resolve_viewer(self, info, **kwargs):
        return ViewerType()
