from decimal import Decimal

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

    return limit_price
