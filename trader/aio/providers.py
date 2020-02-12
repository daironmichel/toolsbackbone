import json
import logging
from datetime import timedelta
from decimal import Decimal

import httpx
from django.utils import timezone
from rauth.utils import OAuth1Auth

from trader.aio.db import database_sync_to_async
from trader.models import ProviderSession, ServiceProvider
from trader.providers import Etrade

# pylint: disable=invalid-name
logger = logging.getLogger("trader.aio.providers")


class AsyncEtrade(Etrade):
    def __init__(self, config: ServiceProvider, stored_session: ProviderSession = None):
        super().__init__(config, stored_session)
        self.name = f'async.etrade.{config.name.lower()}'
        self.log_prefix = f'[{self.name}]'

    @database_sync_to_async
    def _update_session_refreshed_date(self):
        # etrade session goes inactive if no requests made for two hours
        # so we update session.refreshed timestamp here to keep track
        super()._update_session_refreshed_date()

    @database_sync_to_async
    def _get_session_status_from_db(self):
        return super()._get_session_status_from_db()

    def _get_request_auth(self, method: str, url: str, realm='', **kwargs):
        if not self.session:
            return None
        session = self.session
        kwargs.setdefault('headers', {})
        # pylint: disable=protected-access
        oauth_params = session._get_oauth_params(kwargs)
        oauth_params['oauth_signature'] = \
            session.signature.sign(session.consumer_secret,
                                   session.access_token_secret,
                                   method,
                                   url,
                                   oauth_params,
                                   kwargs)
        if 'oauth_signature' not in kwargs['headers'].get('Authorization', ''):
            return OAuth1Auth(oauth_params, realm)
        return None

    async def request(self, method: str, endpoint: str, realm='', **kwargs):
        url = self._get_request_url(method, endpoint, **kwargs)
        auth = self._get_request_auth(method, url, realm=realm, **kwargs)

        self._log_request(method, url, **kwargs)

        async with httpx.AsyncClient(auth=auth) as client:
            response = await client.request(method, url, **kwargs)

        self._log_response(response)
        if response.status_code == 200:
            # etrade session goes inactive if no requests made for two hours
            # so we update session.refreshed timestamp here to keep track
            await self._update_session_refreshed_date()
        return response

    async def get(self, endpoint: str, **kwargs):
        return await self.request("GET", endpoint, **kwargs)

    async def pose(self, endpoint: str, **kwargs):
        return await self.request("POST", endpoint, **kwargs)

    async def put(self, endpoint: str, **kwargs):
        return await self.request("PUT", endpoint, **kwargs)

    async def delete(self, endpoint: str, **kwargs):
        return await self.request("DELETE", endpoint, **kwargs)

    def is_session_active(self) -> bool:
        # Only check status. Access token should be refreshed
        # using the synchronous api.
        if not self.session:
            return False

        status = self.stored_session.status
        refreshed = self.stored_session.refreshed

        if status != ProviderSession.CONNECTED:
            return False

        now = timezone.now()
        return now.date() == refreshed.date() and now - refreshed < timedelta(hours=2)

    async def get_quote(self, symbol):
        response = await self.get(f'/market/quote/{symbol}.json')
        return self._process_get_quote(response)

    async def get_bid_price(self, symbol: str) -> Decimal:
        quote = await self.get_quote(symbol)
        return Decimal(str(quote.get("All").get("bid")))

    async def get_ask_price(self, symbol: str) -> Decimal:
        quote = await self.get_quote(symbol)
        return Decimal(str(quote.get("All").get("bid")))

    async def preview_order(self, account_key, order_client_id, market_session, action,
                            symbol, price_type, quantity, limit_price, stop_price=""):
        headers, payload = self._prepare_preview_order(order_client_id, market_session,
                                                       action, symbol, price_type,
                                                       limit_price, stop_price, quantity)

        # payload = json.dumps(payload)
        response = await self.post(
            f'/accounts/{account_key}/orders/preview.json',
            headers=headers,
            data=json.dumps(payload))

        return self._process_preview_order(response)

    async def place_order(self, account_key, preview_ids, order_client_id, market_session,
                          action, symbol, price_type, quantity, limit_price, stop_price=""):
        headers, payload = self._prepare_place_order(order_client_id, preview_ids,
                                                     market_session, action, symbol,
                                                     price_type, limit_price,
                                                     stop_price, quantity)

        response = await self.post(
            f'/accounts/{account_key}/orders/place.json',
            headers=headers,
            data=json.dumps(payload))

        return self._process_place_order(response)

    async def get_order_details(self, account_key, order_id, symbol):
        headers, params = self._prepare_order_details(symbol)
        response = await self.get(
            f'/accounts/{account_key}/orders.json', params=params, headers=headers)

        return self._process_order_details(order_id, response)

    async def cancel_order(self, account_key, order_id):
        headers, payload = self._prepare_cancel_order(order_id)
        response = await self.put(
            f'/accounts/{account_key}/orders/cancel.json', headers=headers, data=payload)

        return self._process_cancel_order(response)

    async def get_positions(self, account_key):
        response = await self.get(f'/accounts/{account_key}/portfolio.json')

        return self._process_get_positions(response)

    async def get_position(self, account_key, symbol):
        positions = await self.get_positions(account_key)

        return self._process_get_position(symbol, positions)
