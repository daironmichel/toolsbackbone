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


class ViewerCredentialsType(graphene.ObjectType):
    database_id = graphene.Int()
    full_name = graphene.String()

    def resolve_database_id(self, info, **kwargs):
        return info.context.user.id
    full_name = graphene.String()

    def resolve_full_name(self, info, **kwargs):
        user = info.context.user
        return f'{user.first_name} {user.last_name}'.strip() or user.username


class ViewerType(graphene.ObjectType):
    credentials = graphene.Field(ViewerCredentialsType)
    risk_management_settings = graphene.Field(RiskManagementSettingsNode)

    def resolve_credentials(self, info, **kwargs):
        return ViewerCredentialsType()

    def resolve_risk_management_settings(self, info, **kwargs):
        return info.context.user.risk_management_settings


class Query(graphene.ObjectType):
    viewer = graphene.Field(ViewerType)
    risk_management_settings = relay.Node.Field(RiskManagementSettingsNode)

    def resolve_viewer(self, info, **kwargs):
        return ViewerType()
