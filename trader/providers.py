from rauth import OAuth1Service
from .models import ServiceProvider, ProviderSession


class Etrade:
    def __init__(self, config: ServiceProvider):
        self.config = config
        self._service = OAuth1Service(
            name=config.name,
            consumer_key=config.consumer_key,
            consumer_secret=config.consumer_secret,
            request_token_url=config.request_token_url,
            access_token_url=config.access_token_url,
            authorize_url=config.authorize_url,
            base_url=config.base_url
        )

    def get_authorize_url(self) -> str:
        config = self.config
        service = self._service

        request_token, request_token_secret = service.get_request_token(
            params={"oauth_callback": "oob", "format": "json"})

        if config.session:
            config.session.delete()
        config.session = ProviderSession.objects.create(
            request_token=request_token, request_token_secret=request_token_secret)
        config.save()

        return f'{service.authorize_url}?key={service.consumer_key}&token={request_token}'

    def authorize(self, oauth_verifier: str) -> ServiceProvider:
        config = self.config
        service = self._service
        access_token, access_token_secret = service.get_access_token(
            config.session.request_token, config.session.request_token_secret, params={"oauth_verifier": oauth_verifier})

        config.session.access_token = access_token
        config.session.access_token_secret = access_token_secret
        config.session.request_token = None
        config.session.request_token_secret = None
        config.session.status = ProviderSession.CONNECTED
        config.session.save()

        return config

    def get_accounts(self):
        pass
