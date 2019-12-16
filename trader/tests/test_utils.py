from decimal import Decimal

from trader.enums import OrderAction
from trader.utils import get_limit_price


def test__get_limit_price__buy_under_one_dollar__adds_correct_margin():
    margin = Decimal('0.02')

    price1 = Decimal('0.32')
    price2 = Decimal('0.032')
    price3 = Decimal('0.0032')
    price4 = Decimal('0.998')

    result1 = get_limit_price(OrderAction.BUY, price1, margin)
    result2 = get_limit_price(OrderAction.BUY, price2, margin)
    result3 = get_limit_price(OrderAction.BUY_TO_COVER, price3, margin)
    result4 = get_limit_price(OrderAction.BUY_TO_COVER, price4, margin)

    assert result1 == Decimal('0.322')
    assert result2 == Decimal('0.0322')
    assert result3 == Decimal('0.00322')
    assert result4 == Decimal('1')


def test__get_limit_price__sell_under_one_dollar__substracts_correct_margin():
    margin = Decimal('0.02')

    price1 = Decimal('0.32')
    price2 = Decimal('0.032')
    price3 = Decimal('0.0032')
    price4 = Decimal('1.00')

    result1 = get_limit_price(OrderAction.SELL, price1, margin)
    result2 = get_limit_price(OrderAction.SELL, price2, margin)
    result3 = get_limit_price(OrderAction.SELL_SHORT, price3, margin)
    result4 = get_limit_price(OrderAction.SELL_SHORT, price4, margin)

    assert result1 == Decimal('0.318')
    assert result2 == Decimal('0.0318')
    assert result3 == Decimal('0.00318')
    assert result4 == Decimal('0.98')
