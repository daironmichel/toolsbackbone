import enum
from datetime import datetime

import pytz
from django.utils import timezone

from trader.const import NEW_YORK_TZ


class OrderStatus(enum.Enum):
    OPEN = 'OPEN'
    EXECUTED = 'EXECUTED'
    CANCELLED = 'CANCELLED'
    CANCEL_REQUESTED = 'CANCEL_REQUESTED'
    EXPIRED = 'EXPIRED'
    REJECTED = 'REJECTED'
    PARTIAL = 'PARTIAL'


class OrderAction(enum.Enum):
    BUY = 'BUY'
    SELL = 'SELL'
    BUY_TO_COVER = 'BUY_TO_COVER'
    SELL_SHORT = 'SELL_SHORT'

    @staticmethod
    def buying_actions():
        return (OrderAction.BUY, OrderAction.BUY_TO_COVER)

    @staticmethod
    def selling_actions():
        return (OrderAction.SELL, OrderAction.SELL_SHORT)

    def buying(self) -> bool:
        return self in OrderAction.buying_actions()

    def selling(self) -> bool:
        return self in OrderAction.selling_actions()


class MarketSession(enum.Enum):
    REGULAR = 'REGULAR'
    EXTENDED = 'EXTENDED'

    @staticmethod
    def current(otc=False):
        now = timezone.now().astimezone(NEW_YORK_TZ)

        if now.weekday() >= 5:
            return None  # no session on weekends

        premarket_start = now.replace(
            hour=4, minute=0, second=0, microsecond=0)
        market_open = now.replace(
            hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(
            hour=16, minute=0, second=0, microsecond=0)
        afterhours_end = now.replace(
            hour=20, minute=0, second=0, microsecond=0)

        if now < premarket_start or now >= afterhours_end:
            return None

        if market_open <= now < market_close:
            return MarketSession.REGULAR

        return None if otc else MarketSession.EXTENDED


class PriceType(enum.Enum):
    LIMIT = "LIMIT"
    STOP_LIMIT = "STOP_LIMIT"
    MARKET = "MARKET"
