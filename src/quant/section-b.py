# -*- coding: utf-8; py-indent-offset:4 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime

import backtrader as bt
import backtrader.feeds as btfeed
from btplotting import BacktraderPlotting


class firstStrategy(bt.Strategy):
    params = (('maperiod', 5),)

    def log(self, txt, dt=None, doprint=False):
        '''日志函数，用于统一输出日志格式'''
        if doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        self.dataclose = self.datas[0].close

        self.order = None
        self.buyprice = None
        self.buycomm = None

        # 五日移动平均线
        self.sma5 = bt.indicators.SimpleMovingAverage(self.datas[0], period=5)
        # 十日移动平均线
        self.sma10 = bt.indicators.SimpleMovingAverage(self.datas[0], period=10)
        self.sma30 = bt.indicators.SimpleMovingAverage(self.datas[0], period=30)

    def notify_order(self, order):
        """
        订单状态处理

        Arguments:
            order {object} -- 订单状态
        """
        if order.status in [order.Submitted, order.Accepted]:
            # 如订单已被处理，则不用做任何事情
            return

        # 检查订单是否完成
        if order.status in [order.Completed]:
            if order.isbuy():
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            self.bar_executed = len(self)

        # 订单因为缺少资金之类的原因被拒绝执行
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # 订单状态处理完成，设为空
        self.order = None

    def notify_trade(self, trade):
        """
        交易成果

        Arguments:
            trade {object} -- 交易状态
        """
        if not trade.isclosed:
            return

        # 显示交易的毛利率和净利润
        self.log(
            'OPERATION PROFIT, GROSS %.2f, NET %.2f' % (trade.pnl, trade.pnlcomm),
            doprint=True,
        )

    def next(self):
        '''下一次执行'''

        # 记录收盘价
        self.log('Close, %.2f' % self.dataclose[0])

        # 是否正在下单，如果是的话不能提交第二次订单
        if self.order:
            return

        # 是否已经买入
        if not self.position:
            # 还没买，如果 MA5 > MA10 说明涨势，买入
            if self.sma5[0] > self.sma10[0]:
                self.order = self.buy()
        else:
            # 已经买了，如果 MA5 < MA10，说明跌势，卖出
            if self.sma5[0] < self.sma10[0]:
                self.order = self.sell()

    def stop(self):
        self.log(
            u'(金叉死叉有用吗) Ending Value %.2f' % (self.broker.getvalue()), doprint=True
        )


class BSCSVData(btfeed.GenericCSVData):
    params = (
        ("fromdate", datetime.datetime(2020, 1, 1)),
        ("todate", datetime.datetime(2022, 12, 31)),
        ('dtformat', ('%Y-%m-%d')),
        ('openinterest', -1),
    )


if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.addstrategy(firstStrategy)
    cerebro.broker.setcash(1000000.0)
    cerebro.broker.setcommission(commission=0.001)

    data = BSCSVData(dataname="../../datas/baostock/{0}".format('bs_sh.000905.csv'))
    cerebro.adddata(data)
    cerebro.addsizer(bt.sizers.FixedSize, stake=100)

    cash_1 = cerebro.broker.getvalue()
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    cerebro.run()
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
    cash_2 = cerebro.broker.getvalue()

    # 计算总回报率和年度回报率
    return_all = cerebro.broker.getvalue() / 1000000.0
    print(
        'Total ROI: {0}%, Annual ROI{1}%, comm: {2}'.format(
            round((return_all - 1.0) * 100, 2),
            round((pow(return_all, 1.0 / 10) - 1.0) * 100, 2),
            cash_2 - cash_1,
        )
    )

    p = BacktraderPlotting(
        style='bar',
    )
    cerebro.plot(p)
