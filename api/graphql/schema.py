import graphene

from api.graphql import mutations, types

schema = graphene.Schema(query=types.Query, mutation=mutations.Mutation)
