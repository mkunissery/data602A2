import pandas as pd
import numpy as np
import urllib
import requests
import time
import math
import json
import statsmodels.api as sm
import statsmodels.tsa.stattools as ts
import scipy.optimize as sco

from flask import Flask, render_template
from flask import request
from pymongo import MongoClient
from datetime import datetime, timedelta
from statsmodels.tsa.stattools import acf, pacf
from statsmodels.tsa.arima_model import ARIMA
from bson.json_util import dumps

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('Data605_Crypto.html')

@app.route('/opt')
def getopt():
    return render_template('Data605_optimization.html')

@app.route('/Active')
def GetActiveStocks():
    dflog = GetTradeLog()
    dfPos = dflog.groupby(["Ticker",'Symbol']).apply(lambda x: np.sum(x.Qty*x.mult*-1)).reset_index()
    lstCrypto = (( dfPos["Ticker"].str.replace('-',' ') + " (" + dfPos["Symbol"] + ")").loc[dfPos[0] > 0]).tolist()
    return render_template('Data605_SellList.html', clist=lstCrypto)

@app.route('/Shares/<symbol>')
def GetShares(symbol = None):
    dflog = GetTradeLog()
    dfPos = dflog.groupby(['Symbol']).apply(lambda x: np.sum(x.Qty*x.mult*-1)).reset_index()
    idx = dfPos.loc[dfPos["Symbol"] == symbol][0].index[0]
    retval = dfPos.loc[dfPos["Symbol"] == symbol][0][idx]
    return str(retval)

@app.route('/Tradelog')
def GetBlotter():
    dfLog = GetTradeLog()
    dfLogNew = dfLog[['Time','Ticker','Symbol','Qty','Type','Price','Cost','NetCash']]
    if len(dfLogNew)>0:
        return render_template('Data605_Position.html', tables=[dfLogNew.to_html(index=False,formatters = {'Price': '${:,.5f}'.format,'Cost': '${:,.2f}'.format, 'Value': '${:,.2f}'.format,'NetCash': '${:,.2f}'.format, 'Qty': '{:,.4f}'.format})],titles=['na',""])
    else:
        return render_template('Data605_NoPositions.html')

@app.route('/Positions')
def GetOpenPositions():
    dfpos = GetPL()
    dfLogNew = dfpos[['Ticker', 'Position', 'MktPrice', 'Value', 'VWAP', 'UPL', 'RPL', 'TotalPL','PerByShare','PerByDollar','Arima30D','OLS30D' ]]
    if len(dfpos) > 0:
        return render_template('Data605_Position.html', tables=[dfLogNew.to_html(index=False,formatters = {'MktPrice': '${:,.5f}'.format, 'UPL': '${:,.2f}'.format,'Value': '${:,.2f}'.format, 'PerByShare': '{:,.2f}%'.format, 'RPL': '${:,.2f}'.format, 'TotalPL': '${:,.2f}'.format, 'Arima30D': '${:,.2f}'.format, 'OLS30D': '${:,.2f}'.format, 'PerByDollar': '{:,.2f}%'.format})],titles=['na',""])
    else:
        return render_template('Data605_NoPositions.html')


@app.route('/Allocation')
def GetAllocations():
    dfpos = GetPL()
    dfLogNew = dfpos[['Ticker', 'Position', 'MktPrice', 'Value', 'TotalPL','PerByShare','PerByDollar','Max Risk Allocation','Min Risk Allocation' ]]
    if len(dfpos) > 0:
        return render_template('Data605_Position.html', tables=[dfLogNew.to_html(index=False,formatters = {'MktPrice': '${:,.5f}'.format, 'Value': '${:,.2f}'.format, 'PerByShare': '{:,.2f}%'.format,  'TotalPL': '${:,.2f}'.format,  'PerByDollar': '{:,.2f}%'.format , 'Max Risk Allocation': '${:,.2f}'.format , 'Min Risk Allocation': '${:,.2f}'.format})],titles=['na',""])
    else:
        return render_template('Data605_NoPositions.html')


@app.route('/Summary')
def GetSummary():
    dfpos = GetPL()
    totportvalue=dfpos["Value"].sum()
    cashvalue = float(GetCashLevel())
    totreturn = ((totportvalue + cashvalue)/ float(GetInvestableCash()) - 1)*100
    return ('${:20,.2f}'.format(totportvalue) + "~" + '${:20,.2f}'.format(cashvalue) + "~" + '{:20,.2f}%'.format(totreturn)).replace(' ','')


@app.route('/hpl1/', methods=['GET'])
def GetHistoricData():
    measure = request.args.get('measure')
    symbol = request.args.get('coin')
    client = GetMongoClient()
    db = client.Crypto.Datacache
    lookup =  "HPL_" + datetime.now().strftime("%Y%m%d")
    records = db.find({"symbol": lookup})
    if (records.count() > 0):
        recjson = dumps(records)
        bjson = json.loads(recjson)

        dfret = pd.read_json(bjson[0]['data'])
        dfret.columns = ['CashPos', 'Date','MktPrice','Position','RPL','Ticker','TotalPL','UPL','Value','WAP']
        dfret["Date"] = pd.to_datetime(dfret["Date"])
        dfret["Position"] = pd.to_numeric(dfret["Position"])
        dfret["TotalPL"] = pd.to_numeric(dfret["TotalPL"])
        dfret["UPL"] = pd.to_numeric(dfret["UPL"])
        dfret["Value"] = pd.to_numeric(dfret["Value"])
        dfret["WAP"] = pd.to_numeric(dfret["WAP"])
        dfret["CashPos"] = pd.to_numeric(dfret["CashPos"])
        dfret["RPL"] = pd.to_numeric(dfret["RPL"])
        dfretToday = GetHistoricalPL(True)
        frames = [dfret, dfretToday]
        dfret = pd.concat(frames)
    else:
        dfret = GetHistoricalPL(False)
        caches = [
            {
                "symbol": lookup,
                "data": dfret.to_json()
            }
        ]
        for cache in caches:
            db.save(cache)
        #get today.
        dfretToday = GetHistoricalPL(True)
        frames = [dfret, dfretToday]
        dfret = pd.concat(frames)

    if measure != None:
        if measure == "TotalPL":
            dfwap = dfret[dfret.Ticker != "CASH"].groupby(["Date"]).apply(lambda x: np.sum(x[measure]))
        elif measure == "CashPos":
            dfwap = dfret[dfret.Ticker == "CASH"].groupby(["Date"]).apply(lambda x: np.sum(x[measure]))
        elif measure == "WAP":
            dfwap = dfret[dfret.Ticker == symbol].groupby(["Date"]).apply(lambda x: np.sum(x[measure]))

    dfhist = pd.Series.to_frame(dfwap)
    dfhist.columns = [measure]
    series1 = []

    for cdate in dfhist.index:
        hdate = cdate.strftime('%m/%d/%Y')
        hts = int(time.mktime(datetime.strptime(hdate, '%m/%d/%Y').timetuple())) * 1000
        series1.append("[" + str(hts) + "," + str(dfhist.loc[hdate][measure][0]) + "]")

    histdata = "[" + ",".join(series1) + "]"
    return histdata




def perdelta(start, end):
    retlist = []
    curr = start
    while curr <= end:
        retlist.append(curr)
        curr += 1
    return retlist


#def CheckSeriesForStationary(vseries):



@app.route('/arima/<symbol>')
def GetArimaPrediction(symbol = None):
    dfHist =GetHistoricalTimeSeries(symbol)
    price = dfHist.loc[dfHist['close'] > 0]['close']
    lnprice = np.log(price)
    lnprice_diff = lnprice - lnprice.shift()
    lnprice_diff = lnprice_diff[1:len(lnprice_diff)]
    dfret = pd.DataFrame(perdelta(1,30))
    #Auto Correlation
    samplesize = 730

    # acf_1 =  acf(lnprice)[1:samplesize]
    # chartacf = pd.DataFrame([acf_1]).T
    # pacf_1 = pacf(lnprice)[1:samplesize]
    # chartpacf = pd.DataFrame([pacf_1]).T
    #
    # result = ts.adfuller(lnprice, 1)
    # lnprice_diff=lnprice-lnprice.shift()
    # diff=lnprice_diff.dropna()
    # acf_1_diff =  acf(diff)[1:samplesize]
    # chartdiff1 = pd.DataFrame([acf_1_diff]).T
    # chart_pacf_1_diff =  pacf(diff)[1:samplesize]

    #ARIMA
    price_matrix = lnprice.as_matrix()
    model = ARIMA(price_matrix, order=(5, 1, 0))
    model_fit = model.fit(disp=0)
    predictions = model_fit.predict(len(lnprice), len(lnprice)+29, typ='levels')
    predictionsadjusted = np.exp(predictions)
    dfret["sample"] =  predictionsadjusted
    return dfret



@app.route('/hpl/<symbol>')
def GetHistoricalTimeSeries(symbol=None):
    dfret = pd.DataFrame()
    client = GetMongoClient()
    db = client.Crypto.Datacache
    lookup = symbol + "_" + datetime.now().strftime("%Y%m%d") + "_histdata"
    records = db.find({"symbol": lookup })
    if(records.count() > 0):
        dfCache = pd.DataFrame(list(records))
        clist = dfCache['data'][0]
        dfret = pd.DataFrame(clist)
    else:
        series1 = []
        series2 = []
        struri = "https://min-api.cryptocompare.com/data/histoday?fsym=" + symbol + "&tsym=USD&limit=730" #&aggregate=3&e=CCCAGG
        response = requests.get(struri)
        clist = response.json()['Data']
        dfret = pd.DataFrame(clist)
        dfret = dfret.loc[dfret["close"] > 0]
        caches = [
            {
                "symbol": lookup ,
                "data": clist
            }
        ]
        for cache in caches:
            db.save(cache)
    #return render_template('Data605_Position.html', tables=[dfret.to_html()], titles=['na',""])
    return dfret



@app.route('/Getmultiseries/<symbol>')
def GetMovingAverage(symbol=None):
    retval = ""
    client = GetMongoClient()
    db = client.Crypto.Datacache
    lookup = symbol + "_" + datetime.now().strftime("%Y%m%d")
    records = db.find({"symbol": lookup})
    if(records.count() > 0):
        dfCache = pd.DataFrame(list(records))
        retval = dfCache['data'][0]
    else:
        series1 = []
        series2 = []
        struri = "https://min-api.cryptocompare.com/data/histoday?fsym=" + symbol + "&tsym=USD&limit=730" #&aggregate=3&e=CCCAGG
        response = requests.get(struri)
        clist = response.json()['Data']
        df = pd.DataFrame(clist)
        df['sma'] = df["close"].rolling(window=20).mean()
        dfnew = df[['time','close','sma']]
        for index,  row in dfnew.iterrows():
            if math.isnan(row['sma']) != True:  # != pd.np.nan:
                hdate = datetime.fromtimestamp(int(row['time'])).strftime('%m/%d/%Y')
                hts =  int(time.mktime(datetime.strptime(hdate,'%m/%d/%Y').timetuple()))*1000
                series1.append("[" + str(hts) + "," + str(row['close']) + "]")
                series2.append("[" + str(hts) + "," + str(row['sma']) + "]")

        histdata = "[" + ",".join(series1) + "]"
        retval = "[" + ",".join(series1) + "]~["   + ",".join(series2) + "]"
        caches = [
            {
                "symbol": lookup,
                "data": retval
            },
            {
            }
        ]
        for cache in caches:
            db.save(cache)
    return retval

@app.route('/Gethistoricaldata/<symbol>')
def GetHistoricalDataFromCache(symbol=None):
    retval = ""
    client = GetMongoClient()
    db = client.Crypto.Datacache
    lookup = symbol + "_" + datetime.now().strftime("%Y%m%d")
    records = db.find({"symbol": lookup})
    if(records.count() > 0):
        dfCache = pd.DataFrame(list(records))
        retval = dfCache['data'][0]
    else:
        namevalue = []
        struri = "https://min-api.cryptocompare.com/data/histoday?fsym=" + symbol + "&tsym=USD&limit=100" #&aggregate=3&e=CCCAGG
        response = requests.get(struri)
        clist = response.json()['Data']
        df = pd.DataFrame(clist)
        df['SMA'] = df["SMA"].rolling(window=20).mean()
        dfnew = df[['time','close']]
        for index,  row in dfnew.iterrows():
            hdate = datetime.fromtimestamp(int(row['time'])).strftime('%m/%d/%Y')
            hts =  int(time.mktime(datetime.strptime(hdate,'%m/%d/%Y').timetuple()))*1000
            namevalue.append("[" + str(hts) + "," + str(row['close']) + "]")
            retval = "[" + ",".join(namevalue) + "]"
        caches = [{
            "symbol": lookup,
            "data":retval
            }]
        for cache in caches:
            db.save(cache)
    return retval


@app.route('/GetPrice/<coinname>')
def GetPrice(coinname=None):
    coinname = urllib.parse.unquote(coinname)
    coinname = coinname.replace(" ", "-")
    return GetCurrentPrice(coinname)

@app.route('/GetPriceStat/<symbol>')
def GetOneDayPrice(symbol):
    precision = 2
    namevalue = []
    statlist = []
    url = "https://min-api.cryptocompare.com/data/histominute?fsym=" + symbol + "&tsym=USD&limit=1440&aggregate=1"
    response = requests.get(url)
    clist = response.json()['Data']
    if len(clist) > 0:
        cdata = pd.DataFrame(clist)
        curridx = cdata.loc[cdata['time'] == cdata['time'].max()]["close"].index
        cavg = cdata["close"].mean()
        chigh = cdata["high"].max()
        clow = cdata["low"].min()
        curr = cdata.loc[curridx[0]]["close"]
        cstdev = cdata["close"].std()

        for index,  row in cdata.iterrows():
            if index % 60 == 0:
                hdate = datetime.fromtimestamp(int(row['time'])).strftime('%m/%d/%Y %H:%M:%S')
                hts = int(time.mktime(datetime.strptime(hdate, '%m/%d/%Y %H:%M:%S').timetuple())) * 1000
                namevalue.append("[" +  str(hts) + "," + str(row['close']) + "]")
        intradaychartdata =  "[" +  ",".join(namevalue) + "]"
        #",".join(format(x, "10.2f") for x in statlist)
        if curr < 1:
            precision = 3
        statlist = [str(round(curr,precision)),str(round(chigh,precision)),str(round(clow,precision)),str(round(cavg,precision)),str(round(cstdev,precision)),intradaychartdata]
    return "~".join(statlist)

@app.route('/GetCryptoList')
def GetCryptoList():
    lstCrypto = ""
    url = "https://api.coinmarketcap.com/v1/ticker/"
    dfCache = pd.read_json(url)
    lstCrypto =(dfCache["name"] + " (" + dfCache["symbol"] + ")").tolist()
    return render_template('Data605_Trade.html', clist=lstCrypto)

@app.route('/PlaceTrade/', methods=['GET'])
def placeTrade():
    ticker = request.args.get('ticker')
    symbol = request.args.get('symbol')
    price = GetCurrentPrice(symbol)

    ticker = urllib.parse.unquote(ticker)
    ticker = ticker.replace(" ", "-")
    tradetyp = request.args.get('ttype')

    if tradetyp == "B":
        amount = request.args.get('amount')
        qty = float(amount) / float(price)
    else:
        amount = 0
        qty = request.args.get('qty')


    cash = AppendTradeLog(ticker,float(qty),tradetyp,float(price),symbol)
    return str(round(float(price),4))

@app.route('/Getmessagelog')
def GetMessageLog():
    pd.set_option('display.max_colwidth', -1)
    client = GetMongoClient()
    db = client.Crypto.Messagelog
    records = db.find().sort([("Time", 1)])
    dfmessagelog = pd.DataFrame(list(records)).head(10)
    dfm = dfmessagelog[['Message']]
    return render_template('Data605_Position.html', tables=[dfm.to_html(index=False)],titles=['na',""])

@app.route('/Getpie')
def GetPieChart():
    df = GetPL()
    total = 0
    namevalue = []
    for index,  row in df.iterrows():
        if row["Position"] > 0:
            d = {"name": str(row['Ticker']),"y":row["PerByDollar"]}
            namevalue.append(d)
            total = total + row["PerByDollar"]
    if(total < 100):
        d = {"name": "Cash", "y": 100-total}
        namevalue.append(d)
    return json.dumps(namevalue)

@app.route('/Getcash')
def GetCashLevel():
    client = GetMongoClient()
    db = client.Crypto.Crypto
    records = db.find({"name":"cash"})
    if (records.count() == 0):
        cash = [{
            "name": "cash",
            "value": 1000000
        }]
        for data in cash:
            db.save(data)
        records = db.find({"name": "cash"})
        ret = list(records)[0]["value"]
    else:
        ret= list(records)[0]["value"]
    return str(ret)



def GetTradeLog():
    client = GetMongoClient()
    db = client.Crypto.Tradelog
    records = db.find()
    if records.count() > 0:
        dfLog = pd.DataFrame(list(records))
        dfnew = dfLog[['Time', 'Ticker', 'Symbol', 'Qty', 'Type', 'Price', 'Cost', 'NetCash', 'mult', 'ts']]
    else:
        dfnew = pd.DataFrame(
            columns=['Time', 'Ticker', 'Symbol', 'Qty', 'Type', 'Price', 'Cost', 'NetCash', 'mult', 'ts'])
        #listmsg = ["No Trades available"]
        #dfLog = pd.DataFrame({'Message': listmsg})
    return dfnew

def GetCurrentPrice(coinname=None):
    url = "https://min-api.cryptocompare.com/data/price?fsym=" + coinname +"&tsyms=USD"
    response = requests.get(url)
    clist = response.json()
    return str(clist["USD"])


def GetCurrentMultiPrice(coins=None):

    url = "https://min-api.cryptocompare.com/data/pricemulti?fsyms=" + coins + "&tsyms=USD"
    response = requests.get(url)
    clist = response.json()
    return clist

def AppendTradeLog(Ticker, Qty, tType, Price, symbol):
    client = GetMongoClient()
    db = client.Crypto
    dbcash = client.Crypto.Crypto
    tradetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    trd = "Buy"
    sign = -1
    if (tType == "S"):
        trd = "Sell"
        sign = 1

    NetCash = float(GetCashLevel())+(Price*Qty*sign)
    logrec = [{"Ticker": Ticker,
               "Symbol":symbol,
                 "Qty":Qty,
                 "Type": tType,
                 "Price":Price,
                 "Cost":round((Price*Qty),4),
                 "NetCash":NetCash,
                 "Time": tradetime,
                 "mult":sign,
                 "ts":datetime.now().timestamp()
                 }]
    for rec in logrec:
        sign = -1
        db.Tradelog.save(rec)
        cashrec = dbcash.find_one({"name": "cash"})
        dbcash.update_one({"_id": cashrec["_id"]}, {"$set": {"value": NetCash}})

    mlog = [{"Message": tradetime + ": " + trd + " " + str(Qty) + " of " + Ticker ,
             "Time": tradetime
             }]
    for mrec in mlog:
        db.Messagelog.save(mrec)
    return NetCash

def GetMongoClient():
    #client = MongoClient('localhost', 27017)    #use this for local settings
    client = MongoClient('mongodb://mongo:27017')  #use this in a docker setting
    return(client)

def GetInvestableCash():
    client = GetMongoClient()
    db = client.Crypto.Crypto
    records = db.find({"name":"cash2invest"})
    if (records.count() == 0):
        cash = [{
            "name": "cash2invest",
            "value": 1000000
        }]
        for data in cash:
            db.save(data)
        records = db.find({"name": "cash2invest"})
        ret = list(records)[0]["value"]
    else:
        ret= list(records)[0]["value"]
    return ret


def UpdateCashLevel(amount):
    client = GetMongoClient()
    db = client.Crypto.Crypto
    rec = db.find_one({"name": "cash"})
    db.findOneAndUpdate({"name": "cash"},{"$inc": {"value": str(float(rec["value"]) + amount) }})
    return True


def GetPriceHistFromMongo(symbol=None):
    dfCache = pd.DataFrame()
    client = GetMongoClient()
    db = client.Crypto.Datacache
    lookup = symbol + "_" + datetime.now().strftime("%Y%m%d")
    records = db.find({"symbol": lookup + "_hist"})
    if(records.count() > 0):
        dfCache = pd.DataFrame(list(records))
    return dfCache



def CachehistoricalData(coins):
    for ticker in coins:
        GetHistoricalTimeSeries(ticker)
    return True

@app.route('/ols')
def GetOLSPrediction(symbol = None):
    predict = 0
    df = GetHistoricalTimeSeries(symbol)
    df = df.loc[df['time']> 1523664000]
    mintime = np.min(df['time'])
    avg20dayvolume = np.average(df['volumeto'])
    df['time'] = df['time'].apply(lambda x: (x - mintime)/86400)
    nextpointintime = np.max(df['time']) + 30
    df_x = df[['volumeto', 'time']]
    df_y = df[['close']]
    df_x = sm.add_constant(df_x)
    est = sm.OLS(df_y,df_x).fit()
    predict = est.params[0] + est.params[1] * avg20dayvolume + est.params[2] * nextpointintime
    return predict

def GetHistoricalPL(isToday):

    dfTradelog = GetTradeLog()

    if len(dfTradelog) > 0:
        adddays = 0
        tickerlist = dfTradelog['Symbol'].unique().tolist()
        if isToday == False:
            strmindate = dfTradelog.loc[dfTradelog["ts"] ==dfTradelog["ts"].min()]["Time"][0][:10]
            dtmindate =  datetime.strptime(strmindate, "%Y-%m-%d")
        else:
            dtmindate = datetime.today()
            adddays = 1

        pricedict = {}
        dfnew =  pd.DataFrame()
        while dtmindate.date()  < datetime.today().date() + timedelta(days=adddays):
            df = pd.DataFrame(np.empty(0, dtype=[('Ticker', 'S20'),
                                                 ('Position', 'f8'),
                                                 ('MktPrice', 'f8'),
                                                 ('PPrice', 'f8'),
                                                 ('Value', 'f8'),
                                                 ('WAP', 'f8'),
                                                 ('UPL', 'f8'),
                                                 ('RPL', 'f8'),
                                                 ('TotalPL', 'f8'),
                                                 ('CashPos', 'f8'),
                                                 ('PerByDollar', 'f8')
                                                 ]
                                       ))
            #ts = dtmindate.timestamp()
            ts = datetime.strptime(dtmindate.strftime('%Y-%m-%d'), '%Y-%m-%d').timestamp()
            dflog = dfTradelog[dfTradelog['ts'] <= (dtmindate +  timedelta(days=1)).timestamp()]
            dfwap = dflog[dflog.Type == 'B'].groupby(["Symbol"]).apply(lambda x: np.average(x.Price, weights=x.Qty))
            dfsell = dflog[dflog.Type == 'S'].groupby(["Symbol"]).apply(lambda x: np.average(x.Price, weights=x.Qty))
            dfqty = dflog.groupby(["Symbol"]).apply(lambda x: np.sum(x.Qty * x.mult*-1))

            tickerlist = dflog['Symbol'].unique().tolist()

            if isToday :
                coins = ','.join(tickerlist)
                pricelist = GetCurrentMultiPrice(coins)

            tickerlist.append("CASH")
            for ticker in tickerlist:
                df = df.append({'Ticker': ticker}, ignore_index=True)

            df["Date"] = dtmindate

            for ticker in dfwap.index:
                 df.loc[df['Ticker'] == ticker, 'WAP'] = dfwap.loc[ticker]
                 df.loc[df['Ticker'] == ticker, 'UPL'] = 0
                 df.loc[df['Ticker'] == ticker, 'RPL'] = 0

            for ticker in dfqty.index:
                df.loc[df['Ticker'] == ticker, 'Position'] =  dfqty.loc[ticker]

            TotalPos = df['Position'].sum()
            for index, row in df[df['Ticker'].isin(tickerlist)].iterrows():
                rpl = 0
                upl = 0
                bidprice=0
                coin = row['Ticker'].upper()
                if(row['Ticker'].upper() != "CASH"):

                    if coin in pricedict:
                        dfPrice = pricedict[coin]
                    else:
                        dfPrice = GetHistoricalTimeSeries(coin)
                        dfPrice['time'] = dfPrice['time'].apply(
                            lambda x: datetime.strptime((datetime.fromtimestamp(int(str(x))).strftime('%Y-%m-%d')),
                                                        "%Y-%m-%d").timestamp())
                        pricedict[coin] = dfPrice

                    if isToday:
                        cvalue = pricelist[coin]['USD']
                        dftemp = pd.DataFrame()
                        lstcurr = [[cvalue, cvalue, cvalue, cvalue,
                                      int(time.mktime(time.strptime(str(datetime.today().date()), '%Y-%m-%d'))), 0, 0]]
                        dfPrice = dfPrice.append(pd.DataFrame( lstcurr,columns=['close','high', 'low','open','time','volumefrom','volumeto']),ignore_index=True)
                        # dfPrice.loc[-1]
                        #dfPrice.index = dfPrice.index + 1  # shifting index
                        #dfPrice = dfPrice.sort_index()

                    bidprice = dfPrice.loc[dfPrice['time'] == ts]['close'].values[0]
                    df.loc[df['Ticker'] == row['Ticker'], 'MktPrice'] = round(float(bidprice),3)

                    if (row['Position'] > 0):
                        position = float(df.loc[df['Ticker'] == row['Ticker'], 'Position'])
                        wap = float(row['WAP'])
                        upl = (float(bidprice) - wap) * position
                        df.loc[df['Ticker'] == row['Ticker'], 'UPL'] = upl
                        df.loc[df['Ticker'] == row['Ticker'], 'Value'] = position * float(bidprice)

                    sumofsharessold = dflog[(dflog.Type == 'S') & (dflog.Symbol == row['Ticker'])]["Qty"].sum()
                    if (sumofsharessold > 0):
                        position = float(df.loc[df['Ticker'] == row['Ticker'], 'Position'])
                        swap = 0
                        for soldticker in dfsell.index:
                            if soldticker == row['Ticker']:
                                swap = float(dfsell.loc[soldticker])
                        wap = float(row['WAP'])
                        rpl = (swap - wap) * sumofsharessold
                        df.loc[df['Ticker'] == row['Ticker'], 'RPL'] = rpl
                        df.loc[df['Ticker'] == row['Ticker'], 'Value'] = position * float(bidprice)

                    df.loc[df['Ticker'] == row['Ticker'], 'TotalPL'] = upl + rpl
                    df.loc[df['Ticker'] == row['Ticker'], 'CashPos'] = 0
                else:
                    cashpos = 1000000 + (dflog.apply(lambda x: np.sum(x.Qty*x.Price*x.mult), axis=1 ).sum())
                    sumtpl =   df.apply(lambda x: np.sum(x.TotalPL), axis=1).sum()
                    sumvalue = df.apply(lambda x: np.sum(x.Value), axis=1).sum()
                    df.loc[df['Ticker'] == row['Ticker'], 'CashPos'] = cashpos
                    df.loc[df['Ticker'] == "CASH", 'TotalPL'] = sumtpl
                    df.loc[df['Ticker'] == "CASH", 'Value'] = sumvalue
                    df.loc[df['Ticker'] == row['Ticker'], 'Position'] = 0
                    df.loc[df['Ticker'] == row['Ticker'], 'MktPrice'] = 1
                    df.loc[df['Ticker'] == row['Ticker'], 'WAP'] = 0
                    df.loc[df['Ticker'] == row['Ticker'], 'UPL'] = 0
                    df.loc[df['Ticker'] == row['Ticker'], 'RPL'] = 0


            dfnew = dfnew.append(df[['Date','Ticker','Position','MktPrice','Value','WAP','UPL', 'RPL', 'TotalPL','CashPos']],ignore_index=True)
            dtmindate = dtmindate + timedelta(days=1)

    else:
        dfnew = pd.DataFrame()

    dftsPL = dfnew.groupby(["Date"]).apply(lambda x: np.sum(x.TotalPL)).to_frame()
    dftscash = dflog.groupby(["Time"]).apply(lambda x: 1000000 - np.sum(x.Price*x.Qty)).to_frame()
    return dfnew

# Begin Scipi Optimization Algorithm

def portfolio_annualised_performance(weights, mean_returns, cov_matrix):
    returns = np.sum(mean_returns*weights ) *252
    std = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights))) * np.sqrt(252)
    return std, returns

def random_portfolios(num_portfolios, mean_returns, cov_matrix, risk_free_rate):
    results = np.zeros((3,num_portfolios))
    weights_record = []
    for i in range(num_portfolios):
        weights = np.random.random(4)
        weights /= np.sum(weights)
        weights_record.append(weights)
        portfolio_std_dev, portfolio_return = portfolio_annualised_performance(weights, mean_returns, cov_matrix)
        results[0,i] = portfolio_std_dev
        results[1,i] = portfolio_return
        results[2,i] = (portfolio_return - risk_free_rate) / portfolio_std_dev
    return results, weights_record

    #Maximum Sharpe Ratio Portfolio
def neg_sharpe_ratio(weights, mean_returns, cov_matrix, risk_free_rate):
    p_var, p_ret = portfolio_annualised_performance(weights, mean_returns, cov_matrix)
    return -(p_ret - risk_free_rate) / p_var

def max_sharpe_ratio(mean_returns, cov_matrix, risk_free_rate):
    num_assets = len(mean_returns)
    args = (mean_returns, cov_matrix, risk_free_rate)
    constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
    bound = (0.0,1.0)
    bounds = tuple(bound for asset in range(num_assets))
    result = sco.minimize(neg_sharpe_ratio, num_assets*[1./num_assets,], args=args,
                        method='SLSQP', bounds=bounds, constraints=constraints)
    return result

    #Minimum Portfolio Volatility
def portfolio_volatility(weights, mean_returns, cov_matrix):
    return portfolio_annualised_performance(weights, mean_returns, cov_matrix)[0]

def min_variance(mean_returns, cov_matrix):
    num_assets = len(mean_returns)
    args = (mean_returns, cov_matrix)
    constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
    bound = (0.0,1.0)
    bounds = tuple(bound for asset in range(num_assets))

    result = sco.minimize(portfolio_volatility, num_assets*[1./num_assets,], args=args,
                        method='SLSQP', bounds=bounds, constraints=constraints)

    return result


# End Begin Scipi Optimization Algorithm

@app.route('/scopt')
def GetOptimizedPortfolioAllocation(modeltype):
    dflog = GetTradeLog()
    dfCurrPos = dflog.groupby(["Symbol"]).apply(lambda x: np.sum(x.Qty*x.mult*-1))
    obs = []
    assets = 0
    dfAll = pd.DataFrame()
    for symbol in dfCurrPos.index:
        if dfCurrPos[symbol] > 0:
            df = GetHistoricalTimeSeries(symbol)
            dfclose = df["close"].pct_change(1)
            dfclose  = dfclose[len(dfclose)-150:len(dfclose)]
            dfAll[symbol] = dfclose
            obs.append(dfclose)
            assets = assets + 1

    returns = dfAll
    mean_returns = returns.mean()
    cov_matrix = returns.cov()
    risk_free_rate = 0.0184  # as of 5/6/2018
    if modeltype == "max" :
        result = max_sharpe_ratio(mean_returns,cov_matrix,risk_free_rate)
    else:
        result = min_variance(mean_returns, cov_matrix)
    return result



def GetPL():
    df = pd.DataFrame(np.empty(0, dtype=[('Ticker','S20'),
                                         ('Position', 'f8'),
                                         ('MktPrice', 'f8'),
                                         ('Value', 'f8'),
                                         ('VWAP', 'S100'),
                                         ('WAP', 'f8'),
                                         ('UPL', 'f8'),
                                         ('RPL', 'f8'),
                                         ('TotalPL', 'f8'),
                                         ('PerByShare', 'f8'),
                                         ('PerByDollar', 'f8'),
                                         ('Arima30D','f8'),
                                         ('OLS30D','f8'),
                                         ('Max Risk Allocation','f8'),
                                         ('Min Risk Allocation', 'f8')
                                         ]
                               ))
    dflog = GetTradeLog()
    cash2invest = GetInvestableCash()

    if len(dflog) > 0:
        maxoptresult = GetOptimizedPortfolioAllocation("max")
        minoptresult = GetOptimizedPortfolioAllocation("min")
        tickerlist = dflog['Symbol'].unique().tolist()
        coins = ','.join(tickerlist)
        pricelist = GetCurrentMultiPrice(coins)
        dfwap = dflog[dflog.Type == 'B'].groupby(["Symbol"]).apply(lambda x: np.average(x.Price, weights=x.Qty))
        dfsell = dflog[dflog.Type == 'S'].groupby(["Symbol"]).apply(lambda x: np.average(x.Price, weights=x.Qty))
        dfqty = dflog.groupby(["Symbol"]).apply(lambda x: np.sum(x.Qty * x.mult*-1))


        for ticker in tickerlist:
            df = df.append({'Ticker': ticker}, ignore_index=True)

        #tickerlist.append("CASH")
        for ticker in dfwap.index:
             df.loc[df['Ticker'] == ticker, 'WAP'] = dfwap.loc[ticker]
             df.loc[df['Ticker'] == ticker, 'VWAP'] = '<a href=javascript:ChartIt("' + ticker + '")>' + '${:,.2f}'.format(dfwap.loc[ticker]) + '</a>'
             df.loc[df['Ticker'] == ticker, 'UPL'] = 0
             df.loc[df['Ticker'] == ticker, 'RPL'] = 0

        for ticker in dfqty.index:
            df.loc[df['Ticker'] == ticker, 'Position'] =  dfqty.loc[ticker]

        cashlevel = float(GetCashLevel())
        TotalPos = df['Position'].sum()
        portfoliovalue = cash2invest - cashlevel
        Asset = 0
        for index, row in df[df['Ticker'].isin(tickerlist)].iterrows():
            rpl = 0
            upl = 0
            bidprice=0
            if(row['Ticker'].upper() != "CASH"):
                #bidprice = GetCurrentPrice(row['Ticker'])
                bidprice = pricelist[row['Ticker']]['USD']
                df.loc[df['Ticker'] == row['Ticker'], 'MktPrice'] = round(float(bidprice),3)
            else:
                df.loc[df['Ticker'] == row['Ticker'], 'MktPrice'] = 1
                df.loc[df['Ticker'] == row['Ticker'], 'Position'] = cashlevel
                bidprice=1

            if(row['Position'] > 0):
                position = float(df.loc[df['Ticker'] == row['Ticker'], 'Position'])
                wap = float(row['WAP'])
                upl = (float(bidprice)-wap)*position
                df.loc[df['Ticker'] == row['Ticker'], 'UPL'] = upl
                df.loc[df['Ticker'] == row['Ticker'], 'Value'] = position * float(bidprice)
                df.loc[df['Ticker'] == row['Ticker'], 'PerByDollar'] = ((position * float(bidprice)) / cash2invest) * 100
                df.loc[df['Ticker'] == row['Ticker'], 'Arima30D'] = GetArimaPrediction(row['Ticker'])["sample"][29]
                df.loc[df['Ticker'] == row['Ticker'], 'OLS30D'] = GetOLSPrediction(row['Ticker'])
                df.loc[df['Ticker'] == row['Ticker'], 'Max Risk Allocation'] = np.round(maxoptresult.x[Asset] * portfoliovalue ,2)
                df.loc[df['Ticker'] == row['Ticker'], 'Min Risk Allocation'] = np.round(minoptresult.x[Asset] * portfoliovalue, 2)
                Asset = Asset + 1

                if (row['Ticker'].upper() != "CASH"):
                    df.loc[df['Ticker'] == row['Ticker'], 'PerByShare'] = (position / TotalPos) * 100
                else:
                    df.loc[df['Ticker'] == row['Ticker'], 'PerByShare'] = 0

            sumofsharessold = dflog[(dflog.Type == 'S') & (dflog.Symbol==row['Ticker'])]["Qty"].sum()
            if (sumofsharessold > 0):
                position = float(df.loc[df['Ticker'] == row['Ticker'], 'Position'])
                swap = 0
                for soldticker in dfsell.index:
                    if soldticker == row['Ticker']:
                        swap = float(dfsell.loc[soldticker])
                wap = float(row['WAP'])
                rpl = (swap - wap) * sumofsharessold
                df.loc[df['Ticker'] == row['Ticker'], 'RPL'] = rpl
                df.loc[df['Ticker'] == row['Ticker'], 'PerByShare'] = (position / TotalPos) * 100
                df.loc[df['Ticker'] == row['Ticker'], 'PerByDollar'] = ((position * float(bidprice)) / cash2invest) * 100
                df.loc[df['Ticker'] == row['Ticker'], 'Value'] = position * float(bidprice)

            df.loc[df['Ticker'] == row['Ticker'], 'TotalPL'] = upl + rpl
            dfnew =df[['Ticker','Position','MktPrice','Value','WAP','UPL', 'RPL', 'TotalPL', 'PerByShare', 'PerByDollar', 'Arima30D','VWAP','OLS30D','Max Risk Allocation','Min Risk Allocation']]
    else:
        dfnew = df
    return dfnew



if __name__ == "__main__":
    #app.run(debug=True)
    app.run(debug=False, host='0.0.0.0')
