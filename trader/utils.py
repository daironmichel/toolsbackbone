from decimal import Decimal

from .enums import OrderAction


def get_limit_price(action: OrderAction, price: Decimal, margin: Decimal, max_margin: Decimal) -> Decimal:
    # limit_abs_dt = margin
    # limit_max_dt = max_margin

    one_dollar = Decimal('1.00')
    # zero = Decimal(0)
    # two = Decimal(2)
    # ten = Decimal(10)
    # digits = zero

    if price < one_dollar:
        exponent = price.adjusted()
        quantum = Decimal(str(1 / (10**(abs(exponent) + 2))))
        shifted = price.shift(abs(exponent))
        shifted = shifted + margin if action.buying() else shifted - margin
        limit_price = shifted.scaleb(exponent)
        limit_price = limit_price.quantize(quantum)
    else:
        limit_price = price + margin if action.buying() else price - margin

    return limit_price

    # if current_price > one:
    #     while current_price > zero:
    #         digits += one
    #         current_price //= ten
    #     limit_rel_dt = limit_abs_dt / (ten**(digits - one))
    # else:
    #     while current_price < one:
    #         digits += one
    #         current_price *= ten
    #     limit_rel_dt = limit_abs_dt / (ten**(digits + two))

    # limit_rel_dt = round(limit_rel_dt, digits + two)
    # if limit_rel_dt > limit_max_dt:
    #     limit_rel_dt = limit_max_dt

    # if action in buying_actions:
    #     limit_price = current_price + limit_rel_dt
    # else:
    #     limit_price = current_price - limit_rel_dt

    # return round(limit_price, digits + two)
