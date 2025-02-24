from AlgoAPI import AlgoAPIUtil, AlgoAPI_Backtest
from datetime import datetime, timedelta
import talib, numpy

#todo: learn divergence, know more about the rules of the contest

class AlgoEvent:
    def __init__(self):
        self.lasttradetime = datetime(2000,1,1)
        self.start_time = None # the starting time of the trading
        self.arr_close = numpy.array([])
            #self.arr_open = numpy.array([])
        self.ma_len = 20
        self.rsi_len = 14
        self.wait_time = self.ma_len # in days

    def start(self, mEvt):
        self.myinstrument = mEvt['subscribeList'][0]
        self.evt = AlgoAPI_Backtest.AlgoEvtHandler(self, mEvt)
        self.evt.start()

    def on_bulkdatafeed(self, isSync, bd, ab):
        # set start time on the first call of this function
        if not self.start_time:
            self.start_time = bd[self.myinstrument]['timestamp']
        
        # check if it is decision time
        if bd[self.myinstrument]['timestamp'] >= self.lasttradetime + timedelta(hours=24):
            # update arr_close and arr_open
            self.lasttradetime = bd[self.myinstrument]['timestamp']
            lastprice = bd[self.myinstrument]['lastPrice']
                #open_price = bd[self.myinstrument]['openPrice']
            self.arr_close = numpy.append(self.arr_close, lastprice)
                #self.arr_open = numpy.append(self.arr_open, open_price)
            # keep the most recent observations for arr_close (record of close prices)
            if len(self.arr_close)>self.ma_len:
                self.arr_close = self.arr_close[-self.ma_len:]
            """
            # keep the most recent observations for arr_open (record of open prices)
            if len(self.arr_open)>self.ma_len:
                self.arr_open = self.arr_open[-self.ma_len:]"""
            
            # check if we have waited the initial peroid
            if bd[self.myinstrument]['timestamp'] <= self.start_time + timedelta(days = self.wait_time):
                return
            
            # find SMA, upper bband and lower bband
            sma = self.find_sma(self.arr_close, self.ma_len)
            sd = numpy.std(self.arr_close[-self.ma_len::])
            upper_bband = sma + 2*sd
            lower_bband = sma - 2*sd
            
            # debug print result
            self.evt.consoleLog(f"datetime: {bd[self.myinstrument]['timestamp']}")
            self.evt.consoleLog(f"sma: {sma}")
            self.evt.consoleLog(f"upper: {upper_bband}")
            self.evt.consoleLog(f"lower: {lower_bband}")
            
            # check for sell signal (price crosses upper bband and rsi > 70)
            if lastprice >= upper_bband:
                # caclulate the rsi
                rsi = self.find_rsi(self.arr_close, self.rsi_len)
                self.evt.consoleLog(f"rsi: {rsi}")
                # check for rsi
                if rsi > 70:
                    self.test_sendOrder(lastprice, -1, 'open')
                    self.evt.consoleLog(f"sell")
            
            # check for buy signal (price crosses lower bband and rsi < 30)
            if lastprice <= lower_bband:
                # caclulate the rsi
                rsi = self.find_rsi(self.arr_close, self.rsi_len)
                self.evt.consoleLog(f"rsi: {rsi}")
                # check for rsi
                if rsi < 30:
                    self.test_sendOrder(lastprice, 1, "open")
                    self.evt.consoleLog(f"buy")
                
            
            """
            # check number of record is at least greater than both self.fastperiod, self.slowperiod
            if not numpy.isnan(self.arr_fastMA[-1]) and not numpy.isnan(self.arr_fastMA[-2]) and not numpy.isnan(self.arr_slowMA[-1]) and not numpy.isnan(self.arr_slowMA[-2]):
                # send a buy order for Golden Cross
                if self.arr_fastMA[-1] > self.arr_slowMA[-1] and self.arr_fastMA[-2] < self.arr_slowMA[-2]:
                    self.test_sendOrder(lastprice, 1, 'open')
                # send a sell order for Death Cross
                if self.arr_fastMA[-1] < self.arr_slowMA[-1] and self.arr_fastMA[-2] > self.arr_slowMA[-2]:
                    self.test_sendOrder(lastprice, -1, 'open')
            """
            
            
    def on_marketdatafeed(self, md, ab):
        pass

    def on_orderfeed(self, of):
        pass

    def on_dailyPLfeed(self, pl):
        pass

    def on_openPositionfeed(self, op, oo, uo):
        pass
    
    def find_sma(self, data, window_size):
        return data[-window_size::].sum()/window_size
        
    def find_rsi(self, arr_close, window_size):
        # we use previous day's close price as today's open price, which is not entirely accurate
        deltas = numpy.diff(arr_close)
        gains = deltas * (deltas > 0)
        losses = -deltas * (deltas < 0)
    
        avg_gain = numpy.mean(gains[:window_size])
        avg_loss = numpy.mean(losses[:window_size])
    
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
    
        return rsi
        
        
    def test_sendOrder(self, lastprice, buysell, openclose):
        order = AlgoAPIUtil.OrderObject()
        order.instrument = self.myinstrument
        order.orderRef = 1
        if buysell==1:
            order.takeProfitLevel = lastprice*1.1
            order.stopLossLevel = lastprice*0.9
        elif buysell==-1:
            order.takeProfitLevel = lastprice*0.9
            order.stopLossLevel = lastprice*1.1
        order.volume = 10
        order.openclose = openclose
        order.buysell = buysell
        order.ordertype = 0 #0=market_order, 1=limit_order, 2=stop_order
        self.evt.sendOrder(order)