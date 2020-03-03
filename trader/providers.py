import datetime
import json
import logging
import os
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rauth import OAuth1Service

from trader.const import NEY_YORK_TZ

from .models import Account, ProviderSession, ServiceProvider

# pylint: disable=invalid-name
logger = logging.getLogger("trader.providers")
# testlogger = logging.getLogger("testLogger")
# djangologger = logging.getLogger("django")
# toolslogger = logging.getLogger("toolsbackbone")


class ServiceError(Exception):
    def __init__(self, error_code: str, *args):
        super().__init__(*args)
        self.error_code = error_code


def get_provider_instance(config: ServiceProvider):
    return Etrade(config, config.get_stored_session())


class Etrade:
    def __init__(self, config: ServiceProvider, stored_session: ProviderSession = None):
        self.name = f'etrade.{config.name.lower()}'
        self.log_prefix = f'[{self.name}]'
        self.config = config
        self.stored_session = stored_session
        self.service = OAuth1Service(
            name=config.name,
            consumer_key=config.consumer_key,
            consumer_secret=config.consumer_secret,
            request_token_url=config.request_token_url,
            access_token_url=config.access_token_url,
            authorize_url=config.authorize_url,
            base_url=config.base_url
        )

        self.session = None
        if stored_session and stored_session.access_token and stored_session.access_token_secret:
            self.session = self.service.get_session(
                token=(stored_session.access_token, stored_session.access_token_secret))

    def _update_session_refreshed_date(self):
        # etrade session goes inactive if no requests made for two hours
        # so we update session.refreshed timestamp here to keep track
        self.config.session.save()

    def _get_request_url(self, method, endpoint, **kwargs):
        url = self.config.base_url
        if not url.endswith('/'):
            url += '/'
        if endpoint.startswith('/'):
            url += endpoint[1:]
        else:
            url += endpoint

        return url

    def _log_request(self, method, url, **kwargs):
        # to make the code more efficient we only log when debugging
        if os.getenv('DJANGO_LOG_LEVEL', 'INFO') == 'DEBUG':
            logger.debug('%s %s %s', self.log_prefix, method, url)
            logger.debug('%s kwargs: %s', self.log_prefix, kwargs)

    def _log_response(self, response):
        if os.getenv('DJANGO_LOG_LEVEL', 'INFO') == 'DEBUG':
            logger.debug('%s response: %s', self.log_prefix,
                         response.status_code)
            logger.debug('%s content: %s', self.log_prefix,
                         response.json() if response.content else 'EMPTY')

    def request(self, method: str, endpoint: str, realm='', **kwargs):
        url = self._get_request_url(method, endpoint, **kwargs)

        self._log_request(method, url, **kwargs)

        response = self.session.request(
            method, url, header_auth=True, **kwargs)

        self._log_response(response)

        if response.status_code == 200:
            # etrade session goes inactive if no requests made for two hours
            # so we update session.refreshed timestamp here to keep track
            self._update_session_refreshed_date()
        return response

    def get(self, endpoint: str, **kwargs):
        return self.request("GET", endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs):
        return self.request("POST", endpoint, **kwargs)

    def put(self, endpoint: str, **kwargs):
        return self.request("PUT", endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs):
        return self.request("DELETE", endpoint, **kwargs)

    def get_authorize_url(self) -> str:
        service = self.service

        request_token, request_token_secret = service.get_request_token(
            params={"oauth_callback": "oob", "format": "json"})

        config_session = ProviderSession.objects.filter(
            provider=self.config).first()
        if config_session:
            config_session.delete()
        ProviderSession.objects.create(provider=self.config,
                                       request_token=request_token,
                                       request_token_secret=request_token_secret)

        return f'{service.authorize_url}?key={service.consumer_key}&token={request_token}'

    def authorize(self, oauth_verifier: str) -> ServiceProvider:
        config = self.config
        service = self.service
        access_token, access_token_secret = service.get_access_token(
            config.session.request_token,
            config.session.request_token_secret,
            params={"oauth_verifier": oauth_verifier}
        )

        config.session.access_token = access_token
        config.session.access_token_secret = access_token_secret
        config.session.request_token = ''
        config.session.request_token_secret = ''
        config.session.status = ProviderSession.CONNECTED
        config.session.save()

        return config

    def _get_session_status_from_db(self):
        return ProviderSession.objects \
            .filter(provider=self.config) \
            .values_list('status', 'refreshed') \
            .first()

    def is_session_active(self) -> bool:
        config_session = self._get_session_status_from_db()
        if not config_session:
            return False

        status, refreshed = config_session
        if status != ProviderSession.CONNECTED:
            return False

        now = timezone.now()
        if now.date() == refreshed.date() and now - refreshed < timedelta(hours=2):
            return True

        # if access token is older than 2h, try to refresh it
        refresh_url = self.config.refresh_url
        response = self.session.get(refresh_url, header_auth=True)
        if response.status_code != 200:
            return False

        # access token has been refreshed
        self._update_session_refreshed_date()
        return True

    def get_accounts(self) -> dict:
        # request accounts
        response = self.get('/accounts/list.json')

        data = response.json() if response.content else {}
        if not data:
            return None

        accounts_data = data.get("AccountListResponse", {}).get(
            "Accounts", {}).get("Account", None)
        if not accounts_data:
            return None

        return accounts_data

    def get_balance(self, account_key: str, institution_type: str) -> dict:
        # request balance for each account
        headers = {"consumerkey": self.config.consumer_key}
        params = {
            "instType": institution_type,
            "realTimeNAV": "true"
        }
        response = self.get(f'/accounts/{account_key}/balance.json',
                            params=params, headers=headers)

        data = response.json() if response.content else {}

        if not data:
            return None

        return data.get("BalanceResponse", None)

    def sync_accounts(self):
        accounts_data = self.get_accounts()
        for acc_data in accounts_data:
            balance_data = self.get_balance(acc_data.get('accountIdKey'),
                                            acc_data.get('institutionType'))
            computed_balance = balance_data.get('Computed', {})

            account = self.config.broker.accounts.filter(
                account_key=acc_data.get('accountIdKey')).first()

            if not account:
                account = Account()
                account.broker = self.config.broker
                account.provider = self.config
                account.user_id = self.config.broker.user_id

            account_name = acc_data.get('accountName')
            if account_name:
                account.name = account_name
            account.description = acc_data.get('accountDesc')
            account.account_key = acc_data.get('accountIdKey')
            account.account_id = acc_data.get('accountId')
            account.account_mode = acc_data.get('accountMode')
            account.account_status = acc_data.get('accountStatus')
            account.account_type = acc_data.get('accountType')
            account.institution_type = acc_data.get('institutionType')
            account.pdt_status = balance_data.get(
                'dayTraderStatus') or "NOT_AVAILABLE"
            account.account_balance = Decimal(
                str(computed_balance.get('accountBalance', 0)))
            account.net_cash = Decimal(
                str(computed_balance.get('netCash', 0)))
            account.cash_available_for_investment = Decimal(
                str(computed_balance.get('cashAvailableForInvestment', 0)))
            account.cash_balance = Decimal(str(computed_balance.get(
                'cashBalance', 0)))
            account.cash_buying_power = Decimal(str(computed_balance.get(
                'cashBuyingPower', 0)))
            account.margin_buying_power = Decimal(str(computed_balance.get(
                'marginBuyingPower', 0)))
            account.save()

    def _process_get_quote(self, response):
        data = response.json() if response.content else {}

        if response.status_code != 200:
            error = data.get("Error", {})
            code = error.get("code", None)
            msg = error.get("message", "")
            logger.error('%s | Quote symbol failed. Code: %s. Message: %s',
                         response.status_code, code, msg, extra=data)
            raise ServiceError(code,
                               f'Quote symbol failed. {msg}')

        quote_respnse = data.get("QuoteResponse", {})
        quotes = quote_respnse.get("QuoteData", [])
        messages = quote_respnse.get("Messages", {}).get("Message", [])
        if not quotes:
            if messages:
                error = messages[0]
                code = error.get("code", None)
                msg = error.get("description", "")
                logger.error('%s | Quote symbol failed. Code: %s. Message: %s',
                             response.status_code, code, msg, extra=data)
                raise ServiceError(code,
                                   f'Quote symbol failed. {error.get("type")} {code}: {msg}')
            else:
                return None
        elif messages:
            logger.warning('Messages recieved from quote.', extra=data)

        return quotes[0]

    def get_quote(self, symbol):
        response = self.get(f'/market/quote/{symbol}.json')
        return self._process_get_quote(response)

    def get_last_trade_price(self, symbol: str) -> Decimal:
        quote = self.get_quote(symbol)
        return Decimal(str(quote.get("All").get("lastTrade")))

    def get_bid_price(self, symbol: str) -> Decimal:
        quote = self.get_quote(symbol)
        return Decimal(str(quote.get("All").get("bid")))

    def get_ask_price(self, symbol: str) -> Decimal:
        quote = self.get_quote(symbol)
        return Decimal(str(quote.get("All").get("ask")))

    @staticmethod
    def _build_order_payload(market_session, action, symbol, price_type, limit_price, stop_price, quantity):
        return {
            "allOrNone": "false",
            "priceType": price_type,
            "orderTerm": "GOOD_FOR_DAY",
            "marketSession": market_session,
            "stopPrice": str(stop_price),
            "limitPrice": str(limit_price),
            "Instrument": [
                {
                    "Product": {
                        "securityType": "EQ",
                        "symbol": symbol
                    },
                    "orderAction": action,
                    "quantityType": "QUANTITY",
                    "quantity": str(quantity)
                }
            ]
        }

    def _prepare_preview_order(self, order_client_id, market_session, action, symbol,
                               price_type, limit_price, stop_price, quantity):
        if len(str(order_client_id)) > 20:
            raise ValueError(
                "Argument order_client_id is too long. Should be 20 characters or less.")

        headers = {"Content-Type": "application/json",
                   "consumerKey": self.config.consumer_key}

        payload = {
            "PreviewOrderRequest": {
                "orderType": "EQ",
                "clientOrderId": str(order_client_id),
                "Order": [
                    self._build_order_payload(
                        market_session, action, symbol, price_type,
                        limit_price, stop_price, quantity)
                ]
            }
        }
        return headers, payload

    def _process_preview_order(self, response):
        data = response.json() if response.content else {}

        if response.status_code != 200:
            error = data.get("Error", {})
            code = error.get("code", None)
            msg = error.get("message", "")
            logger.error('%s | Preview order failed. Code: %s. Message: %s',
                         response.status_code, code, msg, extra=data)
            raise ServiceError(code,
                               f'Preview order failed. {msg}')

        if not data:
            return None

        preview_ids = []
        for preview in data.get("PreviewOrderResponse", {}).get("PreviewIds", []):
            preview_ids.append(preview.get('previewId'))

        return preview_ids

    def preview_order(self, account_key, order_client_id, market_session, action,
                      symbol, price_type, quantity, limit_price, stop_price=""):
        headers, payload = self._prepare_preview_order(order_client_id, market_session,
                                                       action, symbol, price_type,
                                                       limit_price, stop_price, quantity)

        # payload = json.dumps(payload)
        response = self.post(
            f'/accounts/{account_key}/orders/preview.json',
            headers=headers,
            data=json.dumps(payload))

        return self._process_preview_order(response)

    def _prepare_place_order(self, order_client_id, preview_ids, market_session,
                             action, symbol, price_type, limit_price, stop_price, quantity):
        if len(str(order_client_id)) > 20:
            raise ValueError(
                "Argument order_client_id is too long. Should be 20 characters or less.")

        headers = {"Content-Type": "application/json",
                   "consumerKey": self.config.consumer_key}
        payload = {
            "PlaceOrderRequest": {
                "orderType": "EQ",
                "clientOrderId": str(order_client_id),
                "PreviewIds": [{"previewId": pid} for pid in preview_ids],
                "Order": [
                    self._build_order_payload(
                        market_session, action, symbol, price_type,
                        limit_price, stop_price, quantity)
                ]
            }
        }
        return headers, payload

    def _process_place_order(self, response):
        data = response.json() if response.content else {}

        if response.status_code != 200:
            error = data.get("Error", {})
            code = error.get("code", None)
            msg = error.get("message", "")
            logger.error('%s | Place order failed. Code: %s. Message: %s',
                         response.status_code, code, msg, extra=data)
            raise ServiceError(code,
                               f'Place order failed. {msg}')

        if not data:
            return None

        order_ids = data.get('PlaceOrderResponse', {}).get('OrderIds', None)

        if not order_ids:
            return None

        return order_ids[0].get('orderId')

    def place_order(self, account_key, preview_ids, order_client_id, market_session,
                    action, symbol, price_type, quantity, limit_price, stop_price=""):
        headers, payload = self._prepare_place_order(order_client_id, preview_ids,
                                                     market_session, action, symbol,
                                                     price_type, limit_price,
                                                     stop_price, quantity)

        response = self.post(
            f'/accounts/{account_key}/orders/place.json',
            headers=headers,
            data=json.dumps(payload))

        return self._process_place_order(response)

    def _prepare_order_details(self, symbol):
        params = {"symbol": symbol, "count": 1}
        headers = {"consumerkey": self.config.consumer_key}
        return headers, params

    def _process_order_details(self, order_id, response):
        if response.status_code == 204:
            return None  # Not Found

        data = response.json() if response.content else {}

        if response.status_code != 200:
            logger.error('Order Details Failed.', extra=data)
            error = data.get("Error", {})
            code = error.get("code", None)
            msg = error.get("message", "")
            raise ServiceError(code, f'Order Details Failed. {msg}')

        orders_data = data.get("OrdersResponse", {}).get("Order", [])
        for order in orders_data:
            if order["orderId"] == order_id:
                return order

        return None

    def get_order_details(self, account_key, order_id, symbol):
        headers, params = self._prepare_order_details(symbol)
        response = self.get(
            f'/accounts/{account_key}/orders.json', params=params, headers=headers)

        return self._process_order_details(order_id, response)

    def get_orders(self, account_key, from_date=None, to_date=None):
        now = datetime.datetime.now(NEY_YORK_TZ)
        params = {}
        if not from_date:
            from_date = now - timedelta(days=1)
            params['fromDate'] = from_date.strftime("%m%d%Y")
        if not to_date:
            params['toDate'] = now.strftime("%m%d%Y")

        response = self.get(
            f'/accounts/{account_key}/orders.json', params=params)

        if response.status_code == 204:
            return None  # Not Found

        data = response.json() if response.content else {}

        if response.status_code != 200:
            error = data.get("Error", {})
            code = error.get("code", None)
            msg = error.get("message", "")
            logger.error('%s | Get orders failed. Code: %s. Message: %s',
                         response.status_code, code, msg, extra=data)
            raise ServiceError(code,
                               f'Get orders failed. {msg}')

        return data.get("OrdersResponse", {}).get("Order", None)

    def _prepare_cancel_order(self, order_id):
        headers = {"Content-Type": "application/json",
                   "consumerKey": self.config.consumer_key}

        payload = {
            "CancelOrderRequest": {
                "orderId": order_id
            }
        }

        payload = json.dumps(payload)
        return headers, payload

    def _process_cancel_order(self, response):
        data = response.json() if response.content else {}

        if response.status_code != 200:
            error = data.get("Error", {})
            code = error.get("code", None)
            msg = error.get("message", "")
            logger.error('%s | Cancel order failed. Code: %s. Message: %s',
                         response.status_code, code, msg, extra=data)
            raise ServiceError(code,
                               f'Cancel order failed. {msg}')

        return True

    def cancel_order(self, account_key, order_id):
        headers, payload = self._prepare_cancel_order(order_id)
        response = self.put(
            f'/accounts/{account_key}/orders/cancel.json', headers=headers, data=payload)

        return self._process_cancel_order(response)

    def _process_get_positions(self, response):
        if response.status_code == 204:
            return None  # None Found

        data = response.json() if response.content else {}

        if response.status_code != 200:
            error = data.get("Error", {})
            code = error.get("code", None)
            msg = error.get("message", "")
            logger.error('%s | Get positions failed. Code: %s. Message: %s',
                         response.status_code, code, msg, extra=data)
            raise ServiceError(code,
                               f'Get positions failed. {msg}')

        acc_portfolio = data.get("PortfolioResponse", {}).get(
            "AccountPortfolio", [])

        if not acc_portfolio:
            return None

        return acc_portfolio[0].get('Position', None)

    def get_positions(self, account_key):
        response = self.get(f'/accounts/{account_key}/portfolio.json')

        return self._process_get_positions(response)

    def _process_get_position_quantity(self, symbol, positions):
        for position in positions:
            if position['symbolDescription'] == symbol:
                return position["quantity"]

        return None

    def get_position_quantity(self, account_key, symbol):
        positions = self.get_positions(account_key)

        return self._process_get_position_quantity(symbol, positions)

    def _process_get_position(self, symbol, positions):
        quantity = None
        entry_price = None
        for position in positions:
            if position['symbolDescription'] == symbol:
                quantity = position["quantity"]
                entry_price = Decimal(position["price"])

        return quantity, entry_price

    def get_position(self, account_key, symbol):
        positions = self.get_positions(account_key)

        return self._process_get_position(symbol, positions)

    def get_transactions(self, account_key, from_date=None, to_date=None):
        now = datetime.datetime.now(NEY_YORK_TZ)
        params = {}
        if not from_date:
            from_date = now - timedelta(days=7)
            params['fromDate'] = from_date.strftime("%m%d%Y")
        if not to_date:
            params['toDate'] = now.strftime("%m%d%Y")

        response = self.get(f'/accounts/{account_key}/transactions.json')

        if response.status_code == 204:
            return None  # None Found

        data = response.json() if response.content else {}

        if response.status_code != 200:
            error = data.get("Error", {})
            code = error.get("code", None)
            msg = error.get("message", "")
            logger.error('%s | Get transactions failed. Code: %s. Message: %s',
                         response.status_code, code, msg, extra=data)
            raise ServiceError(code,
                               f'Get transactions failed. {msg}')

        acc_transactions = data.get("TransactionListResponse", {}).get(
            "Transaction", [])

        return acc_transactions

    @staticmethod
    def is_otc(quote):
        primary_exchange = quote.get('All').get('primaryExchange')
        # TODO: find out all exchange codes
        # AMEX, NSDQ, NYSE, PK
        return primary_exchange == 'PK'
