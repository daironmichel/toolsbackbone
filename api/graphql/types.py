# pylint: disable=no-member
import graphene
from graphene import relay
from graphene_django.types import DjangoObjectType

from trader.models import (Broker, ProviderSession, TradingStrategy,
                           ServiceProvider, Account, Position, Order)


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
    def get_node(cls, info, id):
        return ProviderSession.objects.get(id=id)


class ServiceProviderNode(DjangoObjectType):
    session = graphene.Field(ProviderSessionNode)

    class Meta:
        exclude_fields = ('user', 'broker')
        model = ServiceProvider
        interfaces = (relay.Node, DatabaseId)

    @classmethod
    def get_node(cls, info, id):
        return ServiceProvider.objects.get(id=id)


class BrokerNode(DjangoObjectType):
    class Meta:
        exclude_fields = ('user',)
        model = Broker
        interfaces = (relay.Node, DatabaseId)

    @classmethod
    def get_node(cls, info, id):
        return Broker.objects.get(id=id)


class AccountNode(DjangoObjectType):
    class Meta:
        model = Account
        interfaces = (relay.Node, DatabaseId)

    @classmethod
    def get_node(cls, info, id):
        return Account.objects.get(id=id)


class PositionNode(DjangoObjectType):
    class Meta:
        model = Position
        interfaces = (relay.Node, DatabaseId)

    @classmethod
    def get_node(cls, info, id):
        return Position.objects.get(id=id)


class OrderNode(DjangoObjectType):
    class Meta:
        model = Order
        interfaces = (relay.Node, DatabaseId)

    @classmethod
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
    accounts = graphene.Lis(AccountNode)
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
