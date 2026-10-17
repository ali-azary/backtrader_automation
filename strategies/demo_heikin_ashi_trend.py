"""Heikin-Ashi trend demo with a simple percentage trailing exit."""

import backtrader as bt


class DemoHeikinAshi(bt.Indicator):
    """Minimal Heikin-Ashi candle calculation used by the demo strategy."""

    lines = ("ha_open", "ha_high", "ha_low", "ha_close")

    def __init__(self):
        self.l.ha_close = (
            self.data.open + self.data.high + self.data.low + self.data.close
        ) / 4.0

    def next(self):
        if len(self) == 1:
            self.l.ha_open[0] = (self.data.open[0] + self.data.close[0]) / 2.0
        else:
            self.l.ha_open[0] = (
                self.l.ha_open[-1] + self.l.ha_close[-1]
            ) / 2.0
        self.l.ha_high[0] = max(
            self.data.high[0], self.l.ha_open[0], self.l.ha_close[0]
        )
        self.l.ha_low[0] = min(
            self.data.low[0], self.l.ha_open[0], self.l.ha_close[0]
        )


class DemoHeikinAshiTrend(bt.Strategy):
    """Buy a sequence of strong bullish Heikin-Ashi candles."""

    params = (
        ("consecutive_candles", 3),
        ("trail_percent", 0.05),
    )

    def __init__(self):
        self.ha = DemoHeikinAshi(self.data)
        self.entry_order = None
        self.stop_order = None

    def notify_order(self, order):
        if order.status in (order.Submitted, order.Accepted):
            return
        if order.status == order.Completed:
            if self.entry_order and order.ref == self.entry_order.ref:
                self.entry_order = None
                self.stop_order = self.sell(
                    exectype=bt.Order.StopTrail,
                    trailpercent=self.p.trail_percent,
                    size=self.position.size,
                )
            elif self.stop_order and order.ref == self.stop_order.ref:
                self.stop_order = None
        elif order.status in (order.Canceled, order.Margin, order.Rejected):
            if self.entry_order and order.ref == self.entry_order.ref:
                self.entry_order = None
            elif self.stop_order and order.ref == self.stop_order.ref:
                self.stop_order = None

    def next(self):
        if self.entry_order:
            return

        if not self.position:
            strong_bullish_sequence = all(
                self.ha.ha_close[-offset] > self.ha.ha_open[-offset]
                and self.ha.ha_open[-offset] == self.ha.ha_low[-offset]
                for offset in range(self.p.consecutive_candles)
            )
            if strong_bullish_sequence:
                self.entry_order = self.buy()
