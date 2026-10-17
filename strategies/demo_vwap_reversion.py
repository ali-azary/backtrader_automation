"""Rolling-VWAP mean-reversion demo with a trend and volatility filter."""

import backtrader as bt


class DemoVwapReversion(bt.Strategy):
    """Buy a pullback below VWAP during an established rising trend."""

    params = (
        ("vwap_period", 20),
        ("entry_deviation", 0.01),
        ("trend_period", 50),
        ("slope_lookback", 5),
        ("atr_period", 14),
        ("stop_atr", 1.0),
    )

    def __init__(self):
        close = self.data.close
        volume = self.data.volume
        price_volume = close * volume
        self.vwap = (
            bt.indicators.SumN(price_volume, period=self.p.vwap_period)
            / bt.indicators.SumN(volume, period=self.p.vwap_period)
        )
        self.trend = bt.indicators.SMA(close, period=self.p.trend_period)
        self.atr = bt.indicators.ATR(self.data, period=self.p.atr_period)
        self.entry_order = None
        self.exit_order = None
        self.stop_order = None
        self.exit_requested = False

    def notify_order(self, order):
        if order.status in (order.Submitted, order.Accepted):
            return
        if order.status == order.Completed:
            if self.entry_order and order.ref == self.entry_order.ref:
                self.entry_order = None
                self.stop_order = self.sell(
                    exectype=bt.Order.StopTrail,
                    trailamount=max(self.atr[0] * self.p.stop_atr, 0.01),
                    size=self.position.size,
                )
            elif self.stop_order and order.ref == self.stop_order.ref:
                self.stop_order = None
                self.exit_requested = False
            elif self.exit_order and order.ref == self.exit_order.ref:
                self.exit_order = None
                self.exit_requested = False
        elif order.status in (order.Canceled, order.Margin, order.Rejected):
            if self.entry_order and order.ref == self.entry_order.ref:
                self.entry_order = None
            elif self.stop_order and order.ref == self.stop_order.ref:
                self.stop_order = None
            elif self.exit_order and order.ref == self.exit_order.ref:
                self.exit_order = None

    def next(self):
        if self.entry_order or self.exit_order:
            return

        if self.exit_requested:
            if not self.position:
                self.exit_requested = False
            elif self.stop_order is None:
                self.exit_order = self.close()
            return

        close = self.data.close[0]
        trend_is_rising = self.trend[0] > self.trend[-self.p.slope_lookback]
        if not self.position:
            pulled_back = close < self.vwap[0] * (1 - self.p.entry_deviation)
            if pulled_back and trend_is_rising:
                self.entry_order = self.buy()
            return

        if close >= self.vwap[0]:
            self.exit_requested = True
            if self.stop_order and self.stop_order.alive():
                self.cancel(self.stop_order)
