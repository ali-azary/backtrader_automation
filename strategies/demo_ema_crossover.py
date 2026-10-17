"""Simple trend-following demo for the public automation repository."""

import backtrader as bt


class DemoEmaCrossover(bt.Strategy):
    """Buy a bullish EMA crossover and exit on reversal or an ATR trail."""

    params = (
        ("fast_period", 12),
        ("slow_period", 26),
        ("atr_period", 14),
        ("atr_trail", 2.5),
    )

    def __init__(self):
        close = self.data.close
        self.fast = bt.indicators.EMA(close, period=self.p.fast_period)
        self.slow = bt.indicators.EMA(close, period=self.p.slow_period)
        self.cross = bt.indicators.CrossOver(self.fast, self.slow)
        self.atr = bt.indicators.ATR(self.data, period=self.p.atr_period)
        self.order = None
        self.highest_close = None

    def notify_order(self, order):
        if order.status in (order.Submitted, order.Accepted):
            return
        if order.status == order.Completed:
            if order.isbuy():
                self.highest_close = order.executed.price
            elif not self.position:
                self.highest_close = None
        if order.status in (
            order.Completed,
            order.Canceled,
            order.Margin,
            order.Rejected,
        ):
            self.order = None

    def next(self):
        if self.order:
            return

        close = self.data.close[0]
        if not self.position:
            if self.cross[0] > 0:
                self.order = self.buy()
            return

        self.highest_close = max(self.highest_close or close, close)
        trailing_stop = self.highest_close - self.p.atr_trail * self.atr[0]
        if self.cross[0] < 0 or close <= trailing_stop:
            self.order = self.close()
