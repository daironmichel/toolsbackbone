import enum
from datetime import datetime

from trader.const import NEY_YORK_TZ


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
        now = datetime.now(NEY_YORK_TZ)

        if now.weekday() >= 5:
            return None  # no session on weekends

        premarket_start = datetime(
            now.year, now.month, now.day, 4, tzinfo=NEY_YORK_TZ)
        market_open = datetime(
            now.year, now.month, now.day, 9, 30, tzinfo=NEY_YORK_TZ)
        market_close = datetime(
            now.year, now.month, now.day, 16, tzinfo=NEY_YORK_TZ)
        afterhours_end = datetime(
            now.year, now.month, now.day, 20, tzinfo=NEY_YORK_TZ)

        if now < premarket_start or now >= afterhours_end:
            return None

        if market_open <= now < market_close:
            return MarketSession.REGULAR

        return None if otc else MarketSession.EXTENDED


class PriceType(enum.Enum):
    LIMIT = "LIMIT"
    STOP_LIMIT = "STOP_LIMIT"
    MARKET = "MARKET"
