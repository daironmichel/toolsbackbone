import graphene
from graphene import relay
from graphene_django.types import DjangoObjectType
from trader.models import RiskManagementSettings


class RiskManagementSettingsNode(DjangoObjectType):
    class Meta:
        exclude_fields = ('user',)
        model = RiskManagementSettings
        interfaces = (relay.Node, )


class Query(graphene.ObjectType):
    risk_management_settings = relay.Node.Field(RiskManagementSettingsNode)
