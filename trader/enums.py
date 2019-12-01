import datetime
import enum

import pytz


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


class MarketSession(enum.Enum):
    REGULAR = 'REGULAR'
    EXTENDED = 'EXTENDED'

    @staticmethod
    def current():
        ny_tz = pytz.timezone("America/New_York")
        now = datetime.datetime.now(ny_tz)

        if now.weekday >= 5:
            return None  # no session on weekends

        premarket_start = datetime.datetime(
            now.year, now.month, now.day, 4, tzinfo=ny_tz)
        market_open = datetime.datetime(
            now.year, now.month, now.day, 9, 30, tzinfo=ny_tz)
        market_close = datetime.datetime(
            now.year, now.month, now.day, 16, tzinfo=ny_tz)
        afterhours_end = datetime.datetime(
            now.year, now.month, now.day, 20, tzinfo=ny_tz)

        if now < premarket_start or now > afterhours_end:
            return None

        if market_open <= now <= market_close:
            return MarketSession.REGULAR

        return MarketSession.EXTENDED
