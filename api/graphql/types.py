# pylint: disable=no-member
import graphene
from graphene import relay
from graphene_django.types import DjangoObjectType

from trader.models import (Broker, ProviderSession, RiskStrategy,
                           ServiceProvider)


class DatabaseId(graphene.Interface):
    database_id = graphene.Int()

    def resolve_database_id(self, info, **kwargs):
        return getattr(self, 'id')


class RiskStrategyNode(DjangoObjectType):
    class Meta:
        exclude_fields = ('user',)
        model = RiskStrategy
        interfaces = (relay.Node, DatabaseId)

    @classmethod
    def get_node(cls, info, id):
        return RiskStrategy.objects.get(id=id)


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
    risk_strategies = graphene.List(RiskStrategyNode)
    brokers = graphene.List(BrokerNode)

    def resolve_credentials(self, info, **kwargs):
        return ViewerCredentialsType()

    def resolve_risk_strategies(self, info, **kwargs):
        return info.context.user.risk_strategies.all()

    def resolve_brokers(self, info, **kwargs):
        return info.context.user.brokers.all()


class Query(graphene.ObjectType):
    node = relay.Node.Field()
    viewer = graphene.Field(ViewerType)

    def resolve_viewer(self, info, **kwargs):
        return ViewerType()
