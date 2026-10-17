"""Donchian breakout demo with a trend filter and ATR trailing exit."""

import backtrader as bt


class DemoDonchianBreakout(bt.Strategy):
    """Buy a new channel high when price is above its long-term trend."""

    params = (
        ("entry_period", 20),
        ("trend_period", 100),
        ("atr_period", 14),
        ("atr_trail", 3.0),
    )

    def __init__(self):
        self.channel_high = bt.indicators.Highest(
            self.data.high, period=self.p.entry_period
        )
        self.trend = bt.indicators.SMA(
            self.data.close, period=self.p.trend_period
        )
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
            broke_previous_high = close > self.channel_high[-1]
            if broke_previous_high and close > self.trend[0]:
                self.order = self.buy()
            return

        self.highest_close = max(self.highest_close or close, close)
        trailing_stop = self.highest_close - self.p.atr_trail * self.atr[0]
        if close <= trailing_stop:
            self.order = self.close()
