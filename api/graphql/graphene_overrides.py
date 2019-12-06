import re

import graphene


class NonNullConnection(graphene.relay.Connection, abstract=True):
    @classmethod
    def __init_subclass_with_meta__(cls, node=None, name=None, **options):

        if not hasattr(cls, 'Edge'):
            _node = node

            base_name = re.sub("Connection$", "",
                               name or cls.__name__) or _node._meta.name

            class EdgeBase(graphene.ObjectType, name=f'{base_name}Edge'):
                cursor = graphene.String(required=True)
                node = graphene.Field(_node, required=True)

            setattr(cls, 'Edge', EdgeBase)

        if not hasattr(cls, 'edges'):
            setattr(cls, 'edges',
                    graphene.List(graphene.NonNull(cls.Edge), required=True))

        super(NonNullConnection, cls).__init_subclass_with_meta__(
            node=_node,
            name=name,
            **options
        )
