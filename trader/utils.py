from datetime import datetime, timedelta
from decimal import Decimal

from django.utils import timezone

from trader.const import NEW_YORK_TZ

from .enums import OrderAction


def get_limit_price(action: OrderAction, price: Decimal, margin: Decimal) -> Decimal:
    one_dollar = Decimal('1.00')

    if price < one_dollar:
        exponent = price.adjusted()
        quantum = Decimal(str(1 / (10**(abs(exponent) + 2))))
        shifted = price.shift(abs(exponent))
        shifted = shifted + margin if action.buying() else shifted - margin
        limit_price = shifted.scaleb(exponent)
        limit_price = limit_price.quantize(quantum)
    else:
        limit_price = price + margin if action.buying() else price - margin
        limit_price = limit_price.quantize(Decimal('0.01'))

    return limit_price


def get_round_price(price: Decimal) -> Decimal:
    one_dollar = Decimal('1.00')
    if price > one_dollar:
        return price.quantize(Decimal('0.01'))

    exponent = price.adjusted()
    shifted = price.shift(abs(exponent))
    rounded = shifted.quantize(Decimal('0.01'))
    return rounded.scaleb(exponent)


def time_till_market_open(otc=False):
    now = timezone.now().astimezone(NEW_YORK_TZ)
    open_hour = 9 if otc else 4
    open_minute = 30 if otc else 0
    close_hour = 16 if otc else 20
    close_minute = 0
    open_time = now.replace(
        hour=open_hour, minute=open_minute, second=0, microsecond=0)
    close_time = now.replace(
        hour=close_hour, minute=close_minute, second=0, microsecond=0)

    # market is open
    if open_time.weekday() < 5 and open_time <= now < close_time:
        return 0

    # if market already closed today, open is next day
    if close_time <= now:
        open_time += timedelta(days=1)

    # if it's a weekend, open is on Monday
    if open_time.weekday() >= 5:
        open_time += timedelta(days=7 - open_time.weekday())

    time_till_open = open_time - now
    return time_till_open.total_seconds()
