from decimal import Decimal

from trader.models import AutoPilotTask, TradingStrategy


class TestAutoPilotTask:
    def test_loss_amount__returns_correct_value(self):
        strat = TradingStrategy(loss_percent=Decimal('3'))
        auto_pilot = AutoPilotTask(strategy=strat, base_price=Decimal('100'))

        loss_amount = auto_pilot.loss_amount

        assert loss_amount == Decimal('3')

    def test_loss_amount__returns_rounded_value(self):
        strat = TradingStrategy(loss_percent=Decimal('3'))
        auto_pilot1 = AutoPilotTask(
            strategy=strat, base_price=Decimal('4.5324'))
        auto_pilot2 = AutoPilotTask(
            strategy=strat, base_price=Decimal('0.45324'))
        auto_pilot3 = AutoPilotTask(
            strategy=strat, base_price=Decimal('0.045324'))

        loss_amount1 = auto_pilot1.loss_amount
        loss_amount2 = auto_pilot2.loss_amount
        loss_amount3 = auto_pilot3.loss_amount

        assert loss_amount1 == Decimal('0.136')
        assert loss_amount2 == Decimal('0.0136')
        assert loss_amount3 == Decimal('0.00136')

    def test_profit_amount__returns_correct_value(self):
        strat = TradingStrategy(profit_percent=Decimal('8'))
        auto_pilot = AutoPilotTask(strategy=strat, base_price=Decimal('100'))

        profit_amount = auto_pilot.profit_amount

        assert profit_amount == Decimal('8')

    def test_profit_amount__returns_rounded_value(self):
        strat = TradingStrategy(profit_percent=Decimal('8'))
        auto_pilot1 = AutoPilotTask(
            strategy=strat, base_price=Decimal('4.5324'))
        auto_pilot2 = AutoPilotTask(
            strategy=strat, base_price=Decimal('0.45324'))
        auto_pilot3 = AutoPilotTask(
            strategy=strat, base_price=Decimal('0.045324'))

        profit_amount1 = auto_pilot1.profit_amount
        profit_amount2 = auto_pilot2.profit_amount
        profit_amount3 = auto_pilot3.profit_amount

        assert profit_amount1 == Decimal('0.363')
        assert profit_amount2 == Decimal('0.0363')
        assert profit_amount3 == Decimal('0.00363')

    def test_profit_price__returns_correct_value(self):
        strat = TradingStrategy(profit_percent=Decimal('8'))
        auto_pilot = AutoPilotTask(
            strategy=strat,
            base_price=Decimal('10'),
            ref_price=Decimal('10'))

        profit_price = auto_pilot.profit_price

        assert profit_price == Decimal('10.8')

    def test_stop_price__returns_correct_value(self):
        strat = TradingStrategy(loss_percent=Decimal('3'))
        auto_pilot = AutoPilotTask(
            strategy=strat,
            base_price=Decimal('10'),
            ref_price=Decimal('10'))

        stop_price = auto_pilot.stop_price

        assert stop_price == Decimal('9.7')

    def test_stop_price__returns_rounded_value(self):
        strat = TradingStrategy(loss_percent=Decimal('3'))
        auto_pilot1 = AutoPilotTask(
            strategy=strat,
            base_price=Decimal('4.5324'),
            ref_price=Decimal('10'))
        auto_pilot2 = AutoPilotTask(
            strategy=strat,
            base_price=Decimal('0.45324'),
            ref_price=Decimal('1'))
        auto_pilot3 = AutoPilotTask(
            strategy=strat,
            base_price=Decimal('0.045324'),
            ref_price=Decimal('0.1'))

        stop_price1 = auto_pilot1.stop_price
        stop_price2 = auto_pilot2.stop_price
        stop_price3 = auto_pilot3.stop_price

        assert stop_price1 == Decimal('9.86')
        assert stop_price2 == Decimal('0.986')
        assert stop_price3 == Decimal('0.0986')
