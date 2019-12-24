import datetime
import json
import logging
import os
from datetime import timedelta
from decimal import Decimal

import pytz
from django.utils import timezone
from rauth import OAuth1Service

from .models import Account, ProviderSession, ServiceProvider

# pylint: disable=invalid-name
logger = logging.getLogger("trader.providers")
testlogger = logging.getLogger("testLogger")
djangologger = logging.getLogger("django")
toolslogger = logging.getLogger("toolsbackbone")


class ServiceError(Exception):
    pass


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

        config_session = ProviderSession.objects.filter(
            provider=self.config).first()
        if config_session:
            token = (config_session.access_token,
                     config_session.access_token_secret)
            self.session = self._service.get_session(token)

    def request(self, endpoint: str, method: str = "GET", **kwargs):
        url = self._service.base_url
        if not url.endswith('/'):
            url += '/'
        if endpoint.startswith('/'):
            url += endpoint[1:]
        else:
            url += endpoint

        # to make the code more efficient we only log when debugging
        if os.environ.get('DJANGO_LOG_LEVEL', 'INFO') == 'DEBUG':
            logger.debug('%s %s: \n%s %s \nkwargs: %s', self.config.broker.name,
                         self.config.name, method, url, json.dumps(kwargs, indent=2, sort_keys=True))

        if method.upper() == "GET":
            response = self.session.get(url, header_auth=True, **kwargs)
        elif method.upper() == "POST":
            response = self.session.post(url, header_auth=True, **kwargs)
        elif method.upper() == "PUT":
            response = self.session.put(url, header_auth=True, **kwargs)
        elif method.upper() == "DELETE":
            response = self.session.delete(url, header_auth=True, **kwargs)
        else:
            raise NotImplementedError(
                f'Method {method.upper()} is not implemented.')

        if os.environ.get('DJANGO_LOG_LEVEL', 'INFO') == 'DEBUG':
            logger.debug('Response: %s \n%s', response.status_code,
                         json.dumps(response.content.decode('utf-8'), indent=2, sort_keys=True))

        if response.status_code == 200:
            # etrade session goes inactive if no requests made for two hours
            # so we update session.refreshed timestamp here to keep track
            self.config.session.save()
        return response

    def get_authorize_url(self) -> str:
        service = self._service

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
        service = self._service
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

    def is_session_active(self) -> bool:
        config_session = ProviderSession.objects.filter(
            provider=self.config).first()
        if not config_session:
            return False

        if config_session.status != ProviderSession.CONNECTED:
            return False

        now = timezone.now()
        refreshed = config_session.refreshed
        if now.date() == refreshed.date() and now - refreshed < timedelta(hours=2):
            return True

        refresh_url = self.config.refresh_url
        response = self.session.get(refresh_url, header_auth=True)
        return response.status_code == 200

    def get_accounts(self) -> dict:
        # request accounts
        response = self.request('/accounts/list.json')

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
        response = self.request(f'/accounts/{account_key}/balance.json',
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

            account.name = acc_data.get('accountName')
            account.description = acc_data.get('accountDesc')
            account.account_key = acc_data.get('accountIdKey')
            account.account_id = acc_data.get('accountId')
            account.account_mode = acc_data.get('accountMode')
            account.account_status = acc_data.get('accountStatus')
            account.account_type = acc_data.get('accountType')
            account.institution_type = acc_data.get('institutionType')
            account.pdt_status = balance_data.get(
                'dayTraderStatus') or "NOT_AVAILABLE"
            account.cash_balance = Decimal(str(computed_balance.get(
                'cashBalance', 0))) or Decimal(str(computed_balance.get('cashAvailableForInvestment', 0)))
            account.cash_buying_power = Decimal(str(computed_balance.get(
                'cashBuyingPower', 0)))
            account.margin_buying_power = Decimal(str(computed_balance.get(
                'marginBuyingPower', 0)))
            account.save()

    def get_quote(self, symbol):
        response = self.request(f'/market/quote/{symbol}.json')
        data = response.json() if response.content else {}
        quotes = data.get("QuoteResponse", {}).get("QuoteData", None)
        if not quotes:
            return None
        return quotes[0]

    def get_price(self, symbol: str) -> Decimal:
        quote = self.get_quote(symbol)
        return Decimal(str(quote.get("All").get("lastTrade")))

    @staticmethod
    def build_order_payload(market_session, action, symbol, limit_price, quantity):
        return {
            "allOrNone": "false",
            "priceType": "LIMIT",
            "orderTerm": "GOOD_FOR_DAY",
            "marketSession": market_session,
            "stopPrice": "",
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

    def preview_order(self, account_key, order_client_id, market_session, action, symbol, quantity, limit_price):
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
                    self.build_order_payload(
                        market_session, action, symbol, limit_price, quantity)
                ]
            }
        }

        # payload = json.dumps(payload)
        response = self.request(
            f'/accounts/{account_key}/orders/preview.json', headers=headers, data=json.dumps(payload), method="POST")

        data = response.json() if response.content else {}

        if response.status_code != 200:
            error = data.get("Error", {})
            logger.error('%s | Preview order failed. Code: %s. Message: %s',
                         response.status_code, error.get(
                             "code", None), error.get("message", None), extra=data)
            raise ServiceError(
                f'Preview order failed. {error.get("message", "")}')

        if not data:
            return None

        preview_ids = []
        for preview in data.get("PreviewOrderResponse", {}).get("PreviewIds", []):
            preview_ids.append(preview.get('previewId'))

        return preview_ids

    def place_order(self, account_key, preview_ids, order_client_id, market_session,
                    action, symbol, quantity, limit_price):
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
                    self.build_order_payload(
                        market_session, action, symbol, limit_price, quantity)
                ]
            }
        }

        response = self.request(
            f'/accounts/{account_key}/orders/place.json', headers=headers, data=json.dumps(payload), method="POST")

        data = response.json() if response.content else {}

        if response.status_code != 200:
            error = data.get("Error", {})
            logger.error('%s | Place order failed. Code: %s. Message: %s',
                         response.status_code, error.get(
                             "code", None), error.get("message", None), extra=data)
            raise ServiceError(
                f'Place order failed. {error.get("message", "")}')

        if not data:
            return None

        order_ids = data.get('PlaceOrderResponse', {}).get('OrderIds', None)

        if not order_ids:
            return None

        return order_ids[0].get('orderId')

    def get_order_details(self, account_key, order_id, symbol):
        params = {"symbol": symbol}
        headers = {"consumerkey": self.config.consumer_key}
        response = self.request(
            f'/accounts/{account_key}/orders.json', params=params, headers=headers)

        if response.status_code == 204:
            return None  # Not Found

        data = response.json() if response.content else {}

        if response.status_code != 200:
            logger.error('Order Details Failed.', extra=data)
            raise ServiceError('Order Details Failed.')

        orders_data = data.get("OrdersResponse", {}).get("Order", [])
        for order in orders_data:
            if order["orderId"] == order_id:
                return order

        return None

    def get_orders(self, account_key, from_date=None, to_date=None):
        ny_tz = pytz.timezone("America/New_York")
        now = datetime.datetime.now(ny_tz)
        params = {}
        if not from_date:
            from_date = now - timedelta(days=1)
            params['fromDate'] = from_date.strftime("%m%d%Y")
        if not to_date:
            params['toDate'] = now.strftime("%m%d%Y")

        response = self.request(
            f'/accounts/{account_key}/orders.json', params=params)

        if response.status_code == 204:
            return None  # Not Found

        data = response.json() if response.content else {}

        if response.status_code != 200:
            error = data.get("Error", {})
            logger.error('%s | Get orders failed. Code: %s. Message: %s',
                         response.status_code, error.get(
                             "code", None), error.get("message", None), extra=data)
            raise ServiceError(
                f'Get orders failed. {error.get("message", "")}')

        return data.get("OrdersResponse", {}).get("Order", None)

    def cancel_order(self, account_key, order_id):
        headers = {"Content-Type": "application/json",
                   "consumerKey": self.config.consumer_key}

        payload = {
            "CancelOrderRequest": {
                "orderId": order_id
            }
        }

        payload = json.dumps(payload)
        response = self.request(
            f'/accounts/{account_key}/orders/cancel.json', headers=headers, data=payload, method="PUT")

        data = response.json() if response.content else {}

        if response.status_code != 200:
            error = data.get("Error", {})
            logger.error('%s | Cancel order failed. Code: %s. Message: %s',
                         response.status_code, error.get(
                             "code", None), error.get("message", None), extra=data)
            raise ServiceError(
                f'Cancel order failed. {error.get("message", "")}')

        return True

    def get_positions(self, account_key):
        response = self.request(f'/accounts/{account_key}/portfolio.json')

        if response.status_code == 204:
            return None  # None Found

        data = response.json() if response.content else {}

        if response.status_code != 200:
            error = data.get("Error", {})
            logger.error('%s | Get positions failed. Code: %s. Message: %s',
                         response.status_code, error.get(
                             "code", None), error.get("message", None), extra=data)
            raise ServiceError(
                f'Get positions failed. {error.get("message", "")}')

        acc_portfolio = data.get("PortfolioResponse", {}).get(
            "AccountPortfolio", [])

        if not acc_portfolio:
            return None

        return acc_portfolio[0].get('Position', None)

    def get_position_quantity(self, account_key, symbol):
        positions = self.get_positions(account_key)

        for position in positions:
            if position['symbolDescription'] == symbol:
                return position["quantity"]

        return None
