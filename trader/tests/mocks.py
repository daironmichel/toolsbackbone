from datetime import datetime

import pytz

from trader.const import NEW_YORK_TZ

YEAR = 2020
MONTH = 2
MONTH_DST = 3

PREMARKET_START = {
    'year': YEAR, 'month': MONTH,
    'hour': 4, 'minute': 0, 'second': 0, 'microsecond': 0
}
PREMARKET_END = {
    'year': YEAR, 'month': MONTH,
    'hour': 9, 'minute': 29, 'second': 59, 'microsecond': 999999
}
MARKET_START = {
    'year': YEAR, 'month': MONTH,
    'hour': 9, 'minute': 30, 'second': 0, 'microsecond': 0
}
MARKET_END = {
    'year': YEAR, 'month': MONTH,
    'hour': 15, 'minute': 59, 'second': 59, 'microsecond': 999999
}
AFTERHOURS_START = {
    'year': YEAR, 'month': MONTH,
    'hour': 16, 'minute': 0, 'second': 0, 'microsecond': 0
}
AFTERHOURS_END = {
    'year': YEAR, 'month': MONTH,
    'hour': 19, 'minute': 59, 'second': 59, 'microsecond': 999999
}
CLOSED_START = {
    'year': YEAR, 'month': MONTH,
    'hour': 20, 'minute': 0, 'second': 0, 'microsecond': 0
}
CLOSED_END = {
    'year': YEAR, 'month': MONTH,
    'hour': 3, 'minute': 59, 'second': 59, 'microsecond': 999999
}

FRIDAY_PREMARKET_START = NEW_YORK_TZ.localize(datetime(
    day=14, **PREMARKET_START)).astimezone(pytz.utc)
FRIDAY_PREMARKET_END = NEW_YORK_TZ.localize(
    datetime(day=14, **PREMARKET_END)).astimezone(pytz.utc)
FRIDAY_MARKET_START = NEW_YORK_TZ.localize(
    datetime(day=14, **MARKET_START)).astimezone(pytz.utc)
FRIDAY_MARKET_END = NEW_YORK_TZ.localize(
    datetime(day=14, **MARKET_END)).astimezone(pytz.utc)
FRIDAY_AFTERHOURS_START = NEW_YORK_TZ.localize(datetime(
    day=14, **AFTERHOURS_START)).astimezone(pytz.utc)
FRIDAY_AFTERHOURS_END = NEW_YORK_TZ.localize(
    datetime(day=14, **AFTERHOURS_END)).astimezone(pytz.utc)
FRIDAY_CLOSED_START = NEW_YORK_TZ.localize(
    datetime(day=14, **CLOSED_START)).astimezone(pytz.utc)
FRIDAY_CLOSED_END = NEW_YORK_TZ.localize(
    datetime(day=14, **CLOSED_END)).astimezone(pytz.utc)

SATURDAY_PREMARKET_START = NEW_YORK_TZ.localize(datetime(
    day=15, **PREMARKET_START)).astimezone(pytz.utc)
SATURDAY_PREMARKET_END = NEW_YORK_TZ.localize(
    datetime(day=15, **PREMARKET_END)).astimezone(pytz.utc)
SATURDAY_MARKET_START = NEW_YORK_TZ.localize(
    datetime(day=15, **MARKET_START)).astimezone(pytz.utc)
SATURDAY_MARKET_END = NEW_YORK_TZ.localize(
    datetime(day=15, **MARKET_END)).astimezone(pytz.utc)
SUNDAY_AFTERHOURS_START = NEW_YORK_TZ.localize(datetime(
    day=16, **AFTERHOURS_START)).astimezone(pytz.utc)
SUNDAY_AFTERHOURS_END = NEW_YORK_TZ.localize(
    datetime(day=16, **AFTERHOURS_END)).astimezone(pytz.utc)
SUNDAY_CLOSED_START = NEW_YORK_TZ.localize(
    datetime(day=16, **CLOSED_START)).astimezone(pytz.utc)
SUNDAY_CLOSED_END = NEW_YORK_TZ.localize(
    datetime(day=16, **CLOSED_END)).astimezone(pytz.utc)

# DST
PREMARKET_START_DST = PREMARKET_START.copy()
PREMARKET_START_DST.update({'month': MONTH_DST})
PREMARKET_END_DST = PREMARKET_END.copy()
PREMARKET_END_DST.update({'month': MONTH_DST})
MARKET_START_DST = MARKET_START.copy()
MARKET_START_DST.update({'month': MONTH_DST})
MARKET_END_DST = MARKET_END.copy()
MARKET_END_DST.update({'month': MONTH_DST})
AFTERHOURS_START_DST = AFTERHOURS_START.copy()
AFTERHOURS_START_DST.update({'month': MONTH_DST})
AFTERHOURS_END_DST = AFTERHOURS_END.copy()
AFTERHOURS_END_DST.update({'month': MONTH_DST})
CLOSED_START_DST = CLOSED_START.copy()
CLOSED_START_DST.update({'month': MONTH_DST})
CLOSED_END_DST = CLOSED_END.copy()
CLOSED_END_DST.update({'month': MONTH_DST})

FRIDAY_PREMARKET_START_DST = NEW_YORK_TZ.localize(datetime(
    day=13, **PREMARKET_START_DST)).astimezone(pytz.utc)
FRIDAY_PREMARKET_END_DST = NEW_YORK_TZ.localize(datetime(
    day=13, **PREMARKET_END_DST)).astimezone(pytz.utc)
FRIDAY_MARKET_START_DST = NEW_YORK_TZ.localize(datetime(
    day=13, **MARKET_START_DST)).astimezone(pytz.utc)
FRIDAY_MARKET_END_DST = NEW_YORK_TZ.localize(
    datetime(day=13, **MARKET_END_DST)).astimezone(pytz.utc)
FRIDAY_AFTERHOURS_START_DST = NEW_YORK_TZ.localize(datetime(
    day=13, **AFTERHOURS_START_DST)).astimezone(pytz.utc)
FRIDAY_AFTERHOURS_END_DST = NEW_YORK_TZ.localize(datetime(
    day=13, **AFTERHOURS_END_DST)).astimezone(pytz.utc)
FRIDAY_CLOSED_START_DST = NEW_YORK_TZ.localize(datetime(
    day=13, **CLOSED_START_DST)).astimezone(pytz.utc)
FRIDAY_CLOSED_END_DST = NEW_YORK_TZ.localize(
    datetime(day=13, **CLOSED_END_DST)).astimezone(pytz.utc)


def create_datetime(*args, **kw):
    return datetime(*args, **kw)
