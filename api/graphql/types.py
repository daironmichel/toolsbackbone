import graphene
from graphene import relay
from graphene_django.types import DjangoObjectType
from trader.models import RiskManagementSettings


class DatabaseId(graphene.Interface):
    database_id = graphene.Int()

    def resolve_database_id(self, info, **kwargs):
        return getattr(self, 'id')


class RiskManagementSettingsNode(DjangoObjectType):
    class Meta:
        exclude_fields = ('user',)
        model = RiskManagementSettings
        interfaces = (relay.Node, DatabaseId)


class Viewer(graphene.ObjectType):
    risk_management_settings = graphene.Field(RiskManagementSettingsNode)

    def resolve_risk_management_settings(self, info, **kwargs):
        return info.context.user.risk_management_settings


class Query(graphene.ObjectType):
    viewer = graphene.Field(Viewer)
    risk_management_settings = relay.Node.Field(RiskManagementSettingsNode)

    def resolve_viewer(self, info, **kwargs):
        return Viewer()
