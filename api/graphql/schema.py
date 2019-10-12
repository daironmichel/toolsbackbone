import graphene
from api.graphql import types


schema = graphene.Schema(query=types.Query)
