
import json
import logging

from rauth import OAuth1Service

from .models import Account, ProviderSession, ServiceProvider

# pylint: disable=invalid-name
logger = logging.getLogger("trader.providers")


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

    def request(self, endpoint: str, **kwargs):
        url = self._service.base_url
        if not url.endswith('/'):
            url += '/'
        if endpoint.startswith('/'):
            url += endpoint[1:]
        else:
            url += endpoint

        return self.session.get(url, header_auth=True, **kwargs)

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
            config.session.request_token,
            config.session.request_token_secret,
            params={"oauth_verifier": oauth_verifier}
        )

        config.session.access_token = access_token
        config.session.access_token_secret = access_token_secret
        config.session.request_token = None
        config.session.request_token_secret = None
        config.session.status = ProviderSession.CONNECTED
        config.session.save()

        return config

    def get_accounts(self) -> dict:
        # request accounts
        response = self.request('/v1/accounts/list.json')

        data = response.json()
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
        response = self.request(f'/v1/accounts/{account_key}/balance.json',
                                params=params, headers=headers)

        data = response.json()

        if not data:
            return None

        return data.get("BalanceResponse", None)

    def sync_accounts(self):
        accounts_data = self.get_accounts()
        for acc_data in accounts_data:
            balance_data = self.get_balance(acc_data.get('accountIdKey'),
                                            acc_data.get('institutionType'))

            account = self.config.broker.accounts.filter(
                account_key=acc_data.get('accountIdKey')).first()

            if not account:
                account = Account()
                account.broker = self.config.broker
                account.user_id = self.config.broker.user_id

            account.name = acc_data.get('accountName')
            account.description = acc_data.get('accountDesc')
            account.account_key = acc_data.get('accountIdKey')
            account.account_id = acc_data.get('accountId')
            account.account_mode = acc_data.get('accountMode')
            account.account_status = acc_data.get('accountStatus')
            account.account_type = acc_data.get('accountType')
            account.institution_type = acc_data.get('institutionType')
            account.pdt_status = balance_data.get('dayTraderStatus')
            account.cash_balance = balance_data.get(
                'Computed', {}).get('cashBalance', 0)
            account.cash_buying_power = balance_data.get(
                'Computed', {}).get('cashBuyingPower', 0)
            account.margin_buying_power = balance_data.get(
                'Computed', {}).get('marginBuyingPower', 0)
            account.save()

    def get_quote(self, symbol):
        response = self.request(f'/v1/market/quote/{symbol}.json')
        data = response.json()
        quotes = data.get("QuoteResponse", {}).get("QuoteData", None)
        if not quotes:
            return None
        return quotes[0]

    def get_price(self, symbol):
        quote = self.get_quote(symbol)
        return quote.get("All").get("lastTrade")

    @staticmethod
    def build_order_dict(market_session, action, symbol, limit_price, quantity):
        return {
            "allOrNone": "false",
            "priceType": "LIMIT",
            "orderTerm": "GOOD_FOR_DAY",
            "marketSession": market_session,
            "stopPrice": "",
            "limitPrice": limit_price,
            "Instrument": [
                {
                    "Product": {
                        "securityType": "EQ",
                        "symbol": symbol
                    },
                    "orderAction": action,
                    "quantityType": "QUANTITY",
                    "quantity": quantity
                }
            ]
        }

    def preview_order(self, account_key, order_client_id, market_session, action, symbol, quantity, limit_price):
        headers = {"Content-Type": "application/json",
                   "consumerKey": self.config.consumer_key}

        payload = {
            "PlaceOrderRequest": {
                "orderType": "EQ",
                "clientOrderId": order_client_id,
                "Order": [
                    self.build_order_dict(
                        market_session, action, symbol, limit_price, quantity)
                ]
            }
        }

        # payload = """
        #     <PreviewOrderRequest>
        #         <orderType>EQ</orderType>
        #         <clientOrderId>{0}</clientOrderId>
        #         <Order>
        #             <allOrNone>false</allOrNone>
        #             <priceType>LIMIT</priceType>
        #             <orderTerm>GOOD_UNTIL_CANCEL</orderTerm>
        #             <marketSession>{1}</marketSession>
        #             <limitPrice>{2}</limitPrice>
        #             <Instrument>
        #                 <Product>
        #                     <securityType>EQ</securityType>
        #                     <symbol>{3}</symbol>
        #                 </Product>
        #                 <orderAction>{4}</orderAction>
        #                 <quantityType>QUANTITY</quantityType>
        #                 <quantity>{5}</quantity>
        #             </Instrument>
        #         </Order>
        #     </PreviewOrderRequest>
        # """
        # payload = payload.format(
        #     order_client_id, market_session, limit_price, symbol, action, quantity)

        payload = json.dumps(payload)
        response = self.request(
            f'/v1/accounts/{account_key}/orders/preview.json', headers=headers, data=payload)

        data = response.json()

        if response.status_code != 200:
            logger.error('Preview Order Failed.', extra=data)
            raise ServiceError('Preview Order Failed.')

        if not data:
            return None

        preview_ids = []
        for preview in data.get("PreviewOrderResponse", {}).get("PreviewIds", []):
            preview_ids.append(preview.get('previewId'))

        return preview_ids

    def place_order(self, account_key, preview_ids, order_client_id, market_session,
                    action, symbol, quantity, limit_price):
        headers = {"Content-Type": "application/json",
                   "consumerKey": self.config.consumer_key}

        payload = {
            "PlaceOrderRequest": {
                "orderType": "EQ",
                "clientOrderId": order_client_id,
                "PreviewIds": [
                    {"previewId": pid} for pid in preview_ids
                ],
                "Order": [
                    self.build_order_dict(
                        market_session, action, symbol, limit_price, quantity)
                ]
            }
        }

        payload = json.dumps(payload)
        response = self.request(
            f'/v1/accounts/{account_key}/orders/place.json', headers=headers, data=payload)

        data = response.json()

        if response.status_code != 200:
            logger.error('Place Order Failed.', extra=data)
            raise ServiceError('Place Order Failed.')

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
            f'/v1/accounts/{account_key}/orders.json', params=params, headers=headers)

        data = response.json()

        if response.status_code == 204:
            return None  # Not Found

        if response.status_code != 200:
            logger.error('Order Details Failed.', extra=data)
            raise ServiceError('Order Details Failed.')

        orders_data = data.get("OrdersResponse", {}).get("Order", [])
        for order in orders_data:
            if order["orderId"] == order_id:
                return order

        return None

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
            f'/v1/accounts/{account_key}/orders/cancel.json', headers=headers, data=payload)

        data = response.jason()

        if response.status_code != 200:
            logger.error('Cancel Order Failed.', extra=data)
            raise ServiceError('Cancel Order Failed.')

        return True
