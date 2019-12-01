import math

from .enums import OrderAction


def get_limit_price(action, price, margin, max_margin):
    buying_actions = (OrderAction.BUY, OrderAction.BUY_TO_COVER)
    limit_abs_dt = margin
    limit_max_dt = max_margin

    current_price = price
    digits = 0
    if current_price > 1:
        while current_price > 0:
            digits += 1
            current_price //= 10
        limit_rel_dt = limit_abs_dt / math.pow(10, digits - 1)
    else:
        while current_price < 1:
            digits += 1
            current_price *= 10
        limit_rel_dt = limit_abs_dt / math.pow(10, digits + 2)

    limit_rel_dt = round(limit_rel_dt, digits + 2)
    if limit_rel_dt > limit_max_dt:
        limit_rel_dt = limit_max_dt

    if action in buying_actions:
        limit_price = current_price + limit_rel_dt
    else:
        limit_price = current_price - limit_rel_dt

    return round(limit_price, digits + 2)
