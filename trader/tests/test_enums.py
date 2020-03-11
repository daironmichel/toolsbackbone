from datetime import datetime
from unittest import mock

from trader.enums import MarketSession
from trader.tests.mocks import (FRIDAY_AFTERHOURS_END,
                                FRIDAY_AFTERHOURS_END_DST,
                                FRIDAY_AFTERHOURS_START,
                                FRIDAY_AFTERHOURS_START_DST, FRIDAY_CLOSED_END,
                                FRIDAY_CLOSED_END_DST, FRIDAY_CLOSED_START,
                                FRIDAY_CLOSED_START_DST, FRIDAY_MARKET_END,
                                FRIDAY_MARKET_END_DST, FRIDAY_MARKET_START,
                                FRIDAY_MARKET_START_DST, FRIDAY_PREMARKET_END,
                                FRIDAY_PREMARKET_END_DST,
                                FRIDAY_PREMARKET_START,
                                FRIDAY_PREMARKET_START_DST,
                                SATURDAY_MARKET_END, SATURDAY_MARKET_START,
                                SATURDAY_PREMARKET_END,
                                SATURDAY_PREMARKET_START,
                                SUNDAY_AFTERHOURS_END, SUNDAY_AFTERHOURS_START,
                                SUNDAY_CLOSED_END, SUNDAY_CLOSED_START,
                                create_datetime)


class TestMarketSession:
    @mock.patch('trader.enums.timezone')
    def test_current__premarket_start__extended(self, mock_datetime):
        mock_datetime.now.return_value = FRIDAY_PREMARKET_START
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current()

        assert current is MarketSession.EXTENDED

    @mock.patch('trader.enums.timezone')
    def test_current__premarket_end__extended(self, mock_datetime):
        mock_datetime.now.return_value = FRIDAY_PREMARKET_END
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current()

        assert current is MarketSession.EXTENDED

    @mock.patch('trader.enums.timezone')
    def test_current__market_start__regular(self, mock_datetime):
        mock_datetime.now.return_value = FRIDAY_MARKET_START
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current()

        assert current is MarketSession.REGULAR

    @mock.patch('trader.enums.timezone')
    def test_current__market_end__regular(self, mock_datetime):
        mock_datetime.now.return_value = FRIDAY_MARKET_END
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current()

        assert current is MarketSession.REGULAR

    @mock.patch('trader.enums.timezone')
    def test_current__afterhours_start__extended(self, mock_datetime):
        mock_datetime.now.return_value = FRIDAY_AFTERHOURS_START
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current()

        assert current is MarketSession.EXTENDED

    @mock.patch('trader.enums.timezone')
    def test_current__afterhours_end__extended(self, mock_datetime):
        mock_datetime.now.return_value = FRIDAY_AFTERHOURS_END
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current()

        assert current is MarketSession.EXTENDED

    @mock.patch('trader.enums.timezone')
    def test_current__closed_start__none(self, mock_datetime):
        mock_datetime.now.return_value = FRIDAY_CLOSED_START
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current()

        assert current is None

    @mock.patch('trader.enums.timezone')
    def test_current__closed_end__none(self, mock_datetime):
        mock_datetime.now.return_value = FRIDAY_CLOSED_END
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current()

        assert current is None

    @mock.patch('trader.enums.timezone')
    def test_current__weekend_premarket_start__none(self, mock_datetime):
        mock_datetime.now.return_value = SATURDAY_PREMARKET_START
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current()

        assert current is None

    @mock.patch('trader.enums.timezone')
    def test_current__weekend_premarket_end__none(self, mock_datetime):
        mock_datetime.now.return_value = SATURDAY_PREMARKET_END
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current()

        assert current is None

    @mock.patch('trader.enums.timezone')
    def test_current__weekend_market_start__none(self, mock_datetime):
        mock_datetime.now.return_value = SATURDAY_MARKET_START
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current()

        assert current is None

    @mock.patch('trader.enums.timezone')
    def test_current__weekend_market_end__none(self, mock_datetime):
        mock_datetime.now.return_value = SATURDAY_MARKET_END
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current()

        assert current is None

    @mock.patch('trader.enums.timezone')
    def test_current__weekend_afterhours_start__none(self, mock_datetime):
        mock_datetime.now.return_value = SUNDAY_AFTERHOURS_START
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current()

        assert current is None

    @mock.patch('trader.enums.timezone')
    def test_current__weekend_afterhours_end__none(self, mock_datetime):
        mock_datetime.now.return_value = SUNDAY_AFTERHOURS_END
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current()

        assert current is None

    @mock.patch('trader.enums.timezone')
    def test_current__weekend_closed_start__none(self, mock_datetime):
        mock_datetime.now.return_value = SUNDAY_CLOSED_START
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current()

        assert current is None

    @mock.patch('trader.enums.timezone')
    def test_current__weekend_closed_end__none(self, mock_datetime):
        mock_datetime.now.return_value = SUNDAY_CLOSED_END
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current()

        assert current is None

    # -----------------------------------------------------
    #   OTC
    # -----------------------------------------------------

    @mock.patch('trader.enums.timezone')
    def test_current__otc_premarket_start__none(self, mock_datetime):
        mock_datetime.now.return_value = FRIDAY_PREMARKET_START
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current(otc=True)

        assert current is None

    @mock.patch('trader.enums.timezone')
    def test_current__otc_premarket_end__none(self, mock_datetime):
        mock_datetime.now.return_value = FRIDAY_PREMARKET_END
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current(otc=True)

        assert current is None

    @mock.patch('trader.enums.timezone')
    def test_current__otc_market_start__regular(self, mock_datetime):
        mock_datetime.now.return_value = FRIDAY_MARKET_START
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current(otc=True)

        assert current is MarketSession.REGULAR

    @mock.patch('trader.enums.timezone')
    def test_current__otc_market_end__regular(self, mock_datetime):
        mock_datetime.now.return_value = FRIDAY_MARKET_END
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current(otc=True)

        assert current is MarketSession.REGULAR

    @mock.patch('trader.enums.timezone')
    def test_current__otc_afterhours_start__none(self, mock_datetime):
        mock_datetime.now.return_value = FRIDAY_AFTERHOURS_START
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current(otc=True)

        assert current is None

    @mock.patch('trader.enums.timezone')
    def test_current__otc_afterhours_end__none(self, mock_datetime):
        mock_datetime.now.return_value = FRIDAY_AFTERHOURS_END
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current(otc=True)

        assert current is None

    @mock.patch('trader.enums.timezone')
    def test_current__otc_closed_start__none(self, mock_datetime):
        mock_datetime.now.return_value = FRIDAY_CLOSED_START
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current(otc=True)

        assert current is None

    @mock.patch('trader.enums.timezone')
    def test_current__otc_closed_end__none(self, mock_datetime):
        mock_datetime.now.return_value = FRIDAY_CLOSED_END
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current(otc=True)

        assert current is None

    @mock.patch('trader.enums.timezone')
    def test_current__otc_weekend_premarket_start__none(self, mock_datetime):
        mock_datetime.now.return_value = SATURDAY_PREMARKET_START
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current(otc=True)

        assert current is None

    @mock.patch('trader.enums.timezone')
    def test_current__otc_weekend_premarket_end__none(self, mock_datetime):
        mock_datetime.now.return_value = SATURDAY_PREMARKET_END
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current(otc=True)

        assert current is None

    @mock.patch('trader.enums.timezone')
    def test_current__otc_weekend_market_start__none(self, mock_datetime):
        mock_datetime.now.return_value = SATURDAY_MARKET_START
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current(otc=True)

        assert current is None

    @mock.patch('trader.enums.timezone')
    def test_current__otc_weekend_market_end__none(self, mock_datetime):
        mock_datetime.now.return_value = SATURDAY_MARKET_END
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current(otc=True)

        assert current is None

    @mock.patch('trader.enums.timezone')
    def test_current__otc_weekend_afterhours_start__none(self, mock_datetime):
        mock_datetime.now.return_value = SUNDAY_AFTERHOURS_START
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current(otc=True)

        assert current is None

    @mock.patch('trader.enums.timezone')
    def test_current__otc_weekend_afterhours_end__none(self, mock_datetime):
        mock_datetime.now.return_value = SUNDAY_AFTERHOURS_END
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current(otc=True)

        assert current is None

    @mock.patch('trader.enums.timezone')
    def test_current__otc_weekend_closed_start__none(self, mock_datetime):
        mock_datetime.now.return_value = SUNDAY_CLOSED_START
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current(otc=True)

        assert current is None

    @mock.patch('trader.enums.timezone')
    def test_current__otc_weekend_closed_end__none(self, mock_datetime):
        mock_datetime.now.return_value = SUNDAY_CLOSED_END
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current(otc=True)

        assert current is None

    @mock.patch('trader.enums.timezone')
    def test_current__dst_premarket_start__extended(self, mock_datetime):
        mock_datetime.now.return_value = FRIDAY_PREMARKET_START_DST
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current()

        assert current is MarketSession.EXTENDED

    @mock.patch('trader.enums.timezone')
    def test_current__dst_premarket_end__extended(self, mock_datetime):
        mock_datetime.now.return_value = FRIDAY_PREMARKET_END_DST
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current()

        assert current is MarketSession.EXTENDED

    @mock.patch('trader.enums.timezone')
    def test_current__dst_market_start__regular(self, mock_datetime):
        mock_datetime.now.return_value = FRIDAY_MARKET_START_DST
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current()

        assert current is MarketSession.REGULAR

    @mock.patch('trader.enums.timezone')
    def test_current__dst_market_end__regular(self, mock_datetime):
        mock_datetime.now.return_value = FRIDAY_MARKET_END_DST
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current()

        assert current is MarketSession.REGULAR

    @mock.patch('trader.enums.timezone')
    def test_current__dst_afterhours_start__extended(self, mock_datetime):
        mock_datetime.now.return_value = FRIDAY_AFTERHOURS_START_DST
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current()

        assert current is MarketSession.EXTENDED

    @mock.patch('trader.enums.timezone')
    def test_current__dst_afterhours_end__extended(self, mock_datetime):
        mock_datetime.now.return_value = FRIDAY_AFTERHOURS_END_DST
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current()

        assert current is MarketSession.EXTENDED

    @mock.patch('trader.enums.timezone')
    def test_current__dst_closed_start__none(self, mock_datetime):
        mock_datetime.now.return_value = FRIDAY_CLOSED_START_DST
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current()

        assert current is None

    @mock.patch('trader.enums.timezone')
    def test_current__dst_closed_end__none(self, mock_datetime):
        mock_datetime.now.return_value = FRIDAY_CLOSED_END_DST
        mock_datetime.side_effect = create_datetime

        current = MarketSession.current()

        assert current is None
