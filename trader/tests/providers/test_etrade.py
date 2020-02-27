import pytest

from trader.models import ProviderSession, ServiceProvider
from trader.providers import Etrade


class TestEtrade:
    @pytest.fixture
    def config(self):
        return ServiceProvider(
            name='TestProvider',
            consumer_key='consumer_key',
            consumer_secret='consumer_secret',
            request_token_url='request_token_url',
            access_token_url='access_token_url',
            authorize_url='authorize_url',
            base_url='base_url'
        )

    @pytest.fixture
    def stored_session(self):
        return ProviderSession(
            access_token='access_token',
            access_token_secret='access_token_secret'
        )

    def test_init__sets_name(self, config):
        etrade = Etrade(config)
        assert etrade.name == 'etrade.testprovider'

    def test_init__sets_config(self, config):
        etrade = Etrade(config)
        assert etrade.config == config

    def test_init__sets_stored_session(self, config, stored_session):
        etrade = Etrade(config, stored_session)
        assert etrade.stored_session == stored_session

    def test_init__sets_oauth_service(self, config):
        etrade = Etrade(config)
        assert etrade.service is not None
        assert etrade.service.consumer_key == config.consumer_key
        assert etrade.service.consumer_secret == config.consumer_secret
        assert etrade.service.request_token_url == config.request_token_url
        assert etrade.service.access_token_url == config.access_token_url
        assert etrade.service.authorize_url == config.authorize_url
        assert etrade.service.base_url == config.base_url

    def test_init__sets_oauth_session(self, config, stored_session):
        etrade = Etrade(config, stored_session)
        assert etrade.session is not None
        assert etrade.session.access_token == stored_session.access_token
        assert etrade.session.access_token_secret == stored_session.access_token_secret
