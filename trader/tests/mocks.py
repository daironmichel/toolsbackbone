from datetime import datetime

from trader.const import NEY_YORK_TZ

YEAR = 2020
MONTH = 2

PREMARKET_START = {
    'year': YEAR, 'month': MONTH,
    'hour': 4, 'minute': 0, 'second': 0, 'microsecond': 0,
    'tzinfo': NEY_YORK_TZ
}
PREMARKET_END = {
    'year': YEAR, 'month': MONTH,
    'hour': 9, 'minute': 29, 'second': 59, 'microsecond': 999999,
    'tzinfo': NEY_YORK_TZ
}
MARKET_START = {
    'year': YEAR, 'month': MONTH,
    'hour': 9, 'minute': 30, 'second': 0, 'microsecond': 0,
    'tzinfo': NEY_YORK_TZ
}
MARKET_END = {
    'year': YEAR, 'month': MONTH,
    'hour': 15, 'minute': 59, 'second': 59, 'microsecond': 999999,
    'tzinfo': NEY_YORK_TZ
}
AFTERHOURS_START = {
    'year': YEAR, 'month': MONTH,
    'hour': 16, 'minute': 0, 'second': 0, 'microsecond': 0,
    'tzinfo': NEY_YORK_TZ
}
AFTERHOURS_END = {
    'year': YEAR, 'month': MONTH,
    'hour': 19, 'minute': 59, 'second': 59, 'microsecond': 999999,
    'tzinfo': NEY_YORK_TZ
}
CLOSED_START = {
    'year': YEAR, 'month': MONTH,
    'hour': 20, 'minute': 0, 'second': 0, 'microsecond': 0,
    'tzinfo': NEY_YORK_TZ
}
CLOSED_END = {
    'year': YEAR, 'month': MONTH,
    'hour': 3, 'minute': 59, 'second': 59, 'microsecond': 999999,
    'tzinfo': NEY_YORK_TZ
}

FRIDAY_PREMARKET_START = datetime(day=14, **PREMARKET_START)
FRIDAY_PREMARKET_END = datetime(day=14, **PREMARKET_END)
FRIDAY_MARKET_START = datetime(day=14, **MARKET_START)
FRIDAY_MARKET_END = datetime(day=14, **MARKET_END)
FRIDAY_AFTERHOURS_START = datetime(day=14, **AFTERHOURS_START)
FRIDAY_AFTERHOURS_END = datetime(day=14, **AFTERHOURS_END)
FRIDAY_CLOSED_START = datetime(day=14, **CLOSED_START)
FRIDAY_CLOSED_END = datetime(day=14, **CLOSED_END)

SATURDAY_PREMARKET_START = datetime(day=15, **PREMARKET_START)
SATURDAY_PREMARKET_END = datetime(day=15, **PREMARKET_END)
SATURDAY_MARKET_START = datetime(day=15, **MARKET_START)
SATURDAY_MARKET_END = datetime(day=15, **MARKET_END)
SUNDAY_AFTERHOURS_START = datetime(day=16, **AFTERHOURS_START)
SUNDAY_AFTERHOURS_END = datetime(day=16, **AFTERHOURS_END)
SUNDAY_CLOSED_START = datetime(day=16, **CLOSED_START)
SUNDAY_CLOSED_END = datetime(day=16, **CLOSED_END)


def create_datetime(*args, **kw):
    return datetime(*args, **kw)
