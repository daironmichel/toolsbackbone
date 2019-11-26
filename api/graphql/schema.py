import graphene

from api.graphql import mutations, types

# pylint: disable=invalid-name
schema = graphene.Schema(query=types.Query, mutation=mutations.Mutation)
