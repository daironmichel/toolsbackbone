import json
import logging
import os

import httpx
from rauth.utils import OAuth1Auth

from trader.aio.db import database_sync_to_async
from trader.models import ServiceProvider
from trader.providers import Etrade

# pylint: disable=invalid-name
logger = logging.getLogger("trader.aio.providers")


class XEtrade(Etrade):

    @database_sync_to_async
    def _update_session_refreshed_date(self):
        # etrade session goes inactive if no requests made for two hours
        # so we update session.refreshed timestamp here to keep track
        self.config.session.save()

    async def request(self, method: str, endpoint: str, realm='', **kwargs):
        url = self._prepare_request(method, endpoint, **kwargs)

        auth = None
        if self.session:
            session = self.session
            kwargs.setdefault('headers', {})
            oauth_params = session._get_oauth_params(kwargs)
            oauth_params['oauth_signature'] = \
                session.signature.sign(session.consumer_secret,
                                       session.access_token_secret,
                                       method,
                                       url,
                                       oauth_params,
                                       kwargs)
            if 'oauth_signature' not in kwargs['headers'].get('Authorization', ''):
                auth = OAuth1Auth(oauth_params, realm)

        async with httpx.AsyncClient(auth=auth) as client:
            response = await client.request(method, url, **kwargs)

        self._process_response(response)
        if response.status_code == 200:
            # etrade session goes inactive if no requests made for two hours
            # so we update session.refreshed timestamp here to keep track
            await self._update_session_refreshed_date()
        return response

    async def get(self, endpoint: str, **kwargs):
        return await self.request("GET", endpoint, **kwargs)

    async def get_quote(self, symbol):
        response = await self.get(f'/market/quote/{symbol}.json')
        return self._process_get_quote_response(response)
