from datetime import datetime, timedelta
from decimal import Decimal
from unittest import mock

from trader.const import NEY_YORK_TZ
from trader.enums import OrderAction
from trader.tests.mocks import (FRIDAY_AFTERHOURS_END, FRIDAY_AFTERHOURS_START,
                                FRIDAY_CLOSED_END, FRIDAY_CLOSED_START,
                                FRIDAY_MARKET_END, FRIDAY_MARKET_START,
                                FRIDAY_PREMARKET_END, FRIDAY_PREMARKET_START,
                                SATURDAY_MARKET_END, SATURDAY_MARKET_START,
                                SATURDAY_PREMARKET_END,
                                SATURDAY_PREMARKET_START,
                                SUNDAY_AFTERHOURS_END, SUNDAY_AFTERHOURS_START,
                                SUNDAY_CLOSED_END, SUNDAY_CLOSED_START,
                                create_datetime)
from trader.utils import (get_limit_price, get_round_price,
                          time_till_market_open)


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


def test_get_round_price__rounds_correctly():
    price1 = Decimal('4.8373')
    price2 = Decimal('0.48373')
    price3 = Decimal('0.048373')
    price4 = Decimal('4.8323')

    result1 = get_round_price(price1)
    result2 = get_round_price(price2)
    result3 = get_round_price(price3)
    result4 = get_round_price(price4)

    assert result1 == Decimal('4.84')
    assert result2 == Decimal('0.484')
    assert result3 == Decimal('0.0484')
    assert result4 == Decimal('4.83')


@mock.patch('trader.utils.datetime')
def test_time_till_market_open__thursday_closed_start__seconds(mock_datetime):
    mock_datetime.now.return_value = FRIDAY_CLOSED_START - timedelta(days=1)
    mock_datetime.side_effect = create_datetime

    time_till_open = time_till_market_open()

    assert time_till_open == 28800


@mock.patch('trader.utils.datetime')
def test_time_till_market_open__thursday_11pm__seconds(mock_datetime):
    mock_datetime.now.return_value = FRIDAY_PREMARKET_START - \
        timedelta(hours=5)
    mock_datetime.side_effect = create_datetime

    time_till_open = time_till_market_open()

    assert time_till_open == 18000


@mock.patch('trader.utils.datetime')
def test_time_till_market_open__friday_1am__seconds(mock_datetime):
    mock_datetime.now.return_value = FRIDAY_PREMARKET_START - \
        timedelta(hours=3)
    mock_datetime.side_effect = create_datetime

    time_till_open = time_till_market_open()

    assert time_till_open == 10800


@mock.patch('trader.utils.datetime')
def test_time_till_market_open__friday_closed_end__seconds(mock_datetime):
    mock_datetime.now.return_value = FRIDAY_CLOSED_END
    mock_datetime.side_effect = create_datetime

    time_till_open = time_till_market_open()

    assert time_till_open == 0.000001


@mock.patch('trader.utils.datetime')
def test_time_till_market_open__friday_premarket_start__zero(mock_datetime):
    mock_datetime.now.return_value = FRIDAY_PREMARKET_START
    mock_datetime.side_effect = create_datetime

    time_till_open = time_till_market_open()

    assert time_till_open is 0


@mock.patch('trader.utils.datetime')
def test_time_till_market_open__friday_market_start__zero(mock_datetime):
    mock_datetime.now.return_value = FRIDAY_MARKET_START
    mock_datetime.side_effect = create_datetime

    time_till_open = time_till_market_open()

    assert time_till_open is 0


@mock.patch('trader.utils.datetime')
def test_time_till_market_open__friday_market_end__zero(mock_datetime):
    mock_datetime.now.return_value = FRIDAY_MARKET_END
    mock_datetime.side_effect = create_datetime

    time_till_open = time_till_market_open()

    assert time_till_open is 0


@mock.patch('trader.utils.datetime')
def test_time_till_market_open__friday_afterhours_start__zero(mock_datetime):
    mock_datetime.now.return_value = FRIDAY_AFTERHOURS_START
    mock_datetime.side_effect = create_datetime

    time_till_open = time_till_market_open()

    assert time_till_open is 0


@mock.patch('trader.utils.datetime')
def test_time_till_market_open__friday_afterhours_end__zero(mock_datetime):
    mock_datetime.now.return_value = FRIDAY_AFTERHOURS_END
    mock_datetime.side_effect = create_datetime

    time_till_open = time_till_market_open()

    assert time_till_open is 0


@mock.patch('trader.utils.datetime')
def test_time_till_market_open__friday_closed_start_into_weekend__seconds(mock_datetime):
    mock_datetime.now.return_value = FRIDAY_CLOSED_START
    mock_datetime.side_effect = create_datetime

    time_till_open = time_till_market_open()

    assert time_till_open == 201600


@mock.patch('trader.utils.datetime')
def test_time_till_market_open__friday_11pm__seconds(mock_datetime):
    mock_datetime.now.return_value = FRIDAY_CLOSED_START + timedelta(hours=3)
    mock_datetime.side_effect = create_datetime

    time_till_open = time_till_market_open()

    assert time_till_open == 190800


@mock.patch('trader.utils.datetime')
def test_time_till_market_open__saturday_1am__seconds(mock_datetime):
    mock_datetime.now.return_value = FRIDAY_CLOSED_START + timedelta(hours=5)
    mock_datetime.side_effect = create_datetime

    time_till_open = time_till_market_open()

    assert time_till_open == 183600


@mock.patch('trader.utils.datetime')
def test_time_till_market_open__saturday_10am__seconds(mock_datetime):
    mock_datetime.now.return_value = FRIDAY_CLOSED_START + timedelta(hours=14)
    mock_datetime.side_effect = create_datetime

    time_till_open = time_till_market_open()

    assert time_till_open == 151200


@mock.patch('trader.utils.datetime')
def test_time_till_market_open__sunday_10am__seconds(mock_datetime):
    mock_datetime.now.return_value = FRIDAY_CLOSED_START + timedelta(hours=38)
    mock_datetime.side_effect = create_datetime

    time_till_open = time_till_market_open()

    assert time_till_open == 64800
