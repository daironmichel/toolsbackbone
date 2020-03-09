from graphene.test import Client

from api.graphql.mutations import AutoPilotON
from api.graphql.schema import schema

# class TestAutoPilotON:
#     # def setup(self):
#     #     self.client = Client(schema)

#     def test_creates_task(self):
#         client = Client(schema)
#         response = client.execute(
#             '''
#             mutation turnOnAutopilot()
#             ''')
