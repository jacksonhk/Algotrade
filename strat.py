from AlgoAPI import AlgoAPIUtil, AlgoAPI_Backtest
from datetime import datetime, timedelta
import talib, numpy

#todo: learn divergence, know more about the rules of the contest

class AlgoEvent:
    def __init__(self):
        self.lasttradetime = datetime(2000,1,1)
        self.start_time = None # the starting time of the trading
        self.ma_len = 20 # len of arrays of Moving Average
        self.rsi_len = 14 # len of window size in rsi calculation
        self.wait_time = self.ma_len # in days
        self.arr_bbw = numpy.array([])
        self.bbw_len = 1*30 # length of bbw, only set to 30 as too high will yield no sequeeze, may change
        self.arr_close_dict = {} # key to the corresponding arr_close


    def start(self, mEvt):
        self.myinstrument = mEvt['subscribeList'][0]
        self.evt = AlgoAPI_Backtest.AlgoEvtHandler(self, mEvt)
        self.evt.start()


    def on_bulkdatafeed(self, isSync, bd, ab):
        # set start time and arr_close(s) of all instruments in bd on the first call of this function
        if not self.start_time:
            self.start_time = bd[self.myinstrument]['timestamp']
            for key in bd:
                #self.evt.consoleLog(f"stock dict: {bd[key]}")
                self.arr_close_dict[key] = numpy.array([])
        
        # check if it is decision time
        if bd[self.myinstrument]['timestamp'] >= self.lasttradetime + timedelta(hours=24):
            # update arr_close(s)
            self.lasttradetime = bd[self.myinstrument]['timestamp']
            #self.evt.consoleLog(f"wwwwwwwwwwwwwwwwwwwwwwwwwwwwwww")
            for key in bd:
                lastprice = bd[key]['lastPrice']
                arr_close = self.arr_close_dict[key]
                #self.evt.consoleLog(f"arr close: {arr_close}")
                
                
                self.arr_close_dict[key] = numpy.append(self.arr_close_dict[key], lastprice)
            
                # keep the most recent observations for arr_close (record of close prices)
                self.arr_close_dict[key] = self.arr_close_dict[key][-self.ma_len::]
            
            # check if we have waited the initial peroid
            if bd[self.myinstrument]['timestamp'] <= self.start_time + timedelta(days = self.wait_time):
                return
            
            # execute the trading strat for all instruments
            for key in bd:
                self.execute_strat(bd, key)
            
            
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

    # execute the trading strat for one instructment given the key and bd       
    def execute_strat(self, bd, key):
        self.evt.consoleLog("---------------------------------")
        self.evt.consoleLog("Executing strat")

        # find sma, sd, 2 bbands, bbw, and lastprice
        arr_close = self.arr_close_dict[key]
        sma = self.find_sma(arr_close, self.ma_len)
        sd = numpy.std(arr_close)
        upper_bband = sma + 2*sd
        lower_bband = sma - 2*sd
        bbw = (upper_bband-lower_bband)/sma
        lastprice = arr_close[-1]
        
        #sequeeze? (maybe remove)
        is_sequeeze = False
        #self.arr_bbw = numpy.append(self.arr_bbw, bbw)
        #self.arr_bbw = self.arr_bbw[-self.bbw_len::]
        #is_sequeeze = self.is_sequeeze(self.arr_bbw)
        
        # debug
        self.evt.consoleLog(f"name of instrument: { bd[key]['instrument'] }")
        #self.evt.consoleLog(f"datetime: {bd[self.myinstrument]['timestamp']}")
        #self.evt.consoleLog(f"sma: {sma}")
        #self.evt.consoleLog(f"upper: {upper_bband}")
        #self.evt.consoleLog(f"lower: {lower_bband}")
        #self.evt.consoleLog(f"bbw: {bbw}")
        
        # check for sell signal (price cross upper bband from above and rsi > 70)
        if lastprice <= upper_bband and arr_close[-2] >= upper_bband:
            # caclulate the rsi
            rsi = self.find_rsi(arr_close, self.rsi_len)
            self.evt.consoleLog(f"rsi: {rsi}")
            # check for rsi
            if rsi > 70:
                self.test_sendOrder(lastprice, -1, 'open', self.find_positionSize(lastprice, is_sequeeze))
                self.evt.consoleLog(f"SELL SELL SELL SELL")
                
        # check for buy signal (price cross lower bband from below and rsi < 30)
        if lastprice >= lower_bband and arr_close[-2] <= upper_bband:
            # caclulate the rsi
            rsi = self.find_rsi(arr_close, self.rsi_len)
            self.evt.consoleLog(f"rsi: {rsi}")
            # check for rsi
            if rsi < 30:
                self.test_sendOrder(lastprice, 1, "open", self.find_positionSize(lastprice, is_sequeeze))
                self.evt.consoleLog(f"BUY BUY BUY BUY")
                
        self.evt.consoleLog("Executed strat")
        self.evt.consoleLog("---------------------------------")
        
        
    # determine if there is bollinger squeeze
    def is_sequeeze(self, arr_bbw):
        if len(arr_bbw) < self.bbw_len:
            return False
        return arr_bbw[-1] == arr_bbw.min()
    
    
    def find_rsi(self, arr_close, window_size):
        rsi_arr = talib.RSI(arr_close, window_size)
        cur_rsi = rsi_arr[-1]
        return cur_rsi
        
        
    def test_sendOrder(self, lastprice, buysell, openclose, volume = 10):
        order = AlgoAPIUtil.OrderObject()
        order.instrument = self.myinstrument
        order.orderRef = 1
        if buysell==1:
            order.takeProfitLevel = lastprice*1.1
            order.stopLossLevel = lastprice*0.9
        elif buysell==-1:
            order.takeProfitLevel = lastprice*0.9
            order.stopLossLevel = lastprice*1.1
        order.volume = volume
        order.openclose = openclose
        order.buysell = buysell
        order.ordertype = 0 #0=market_order, 1=limit_order, 2=stop_order
        self.evt.sendOrder(order)

    # utility function to find volume based on available balance
    def find_positionSize(self, lastprice, is_sequeeze):
        res = self.evt.getAccountBalance()
        availableBalance = res["availableBalance"]
        ratio = 0.3
        volume = (availableBalance*ratio) / lastprice
        total =  availableBalance*ratio
        while total < 0.3 * availableBalance:
            ratio *= 1.05
            volume = (availableBalance*ratio) / lastprice
            total = availableBalance*ratio
        while total > availableBalance:
            ratio *= 0.95
            volume = (availableBalance*ratio) / lastprice
            total = availableBalance*ratio
        if is_sequeeze:
            volume *= 5
        return volume*1000
