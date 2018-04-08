from flask import Flask, render_template
from flask import request
from pymongo import MongoClient
import pandas as pd
import numpy as np
import json
import urllib
from datetime import datetime
import requests
import time
import math
import socket


app = Flask(__name__)


@app.route('/')
def index():
    return render_template('Data605_Crypto.html')

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
    if len(dfpos) > 0:
        return render_template('Data605_Position.html', tables=[dfpos.to_html(index=False,formatters = {'MktPrice': '${:,.5f}'.format,'WAP': '${:,.2f}'.format, 'UPL': '${:,.2f}'.format,'Value': '${:,.2f}'.format, 'PerByShare': '{:,.2f}%'.format, 'RPL': '${:,.2f}'.format, 'TotalPL': '${:,.2f}'.format, 'PerByDollar': '{:,.2f}%'.format})],titles=['na',""])
    else:
        return render_template('Data605_NoPositions.html')





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
        struri = "https://min-api.cryptocompare.com/data/histoday?fsym=" + symbol + "&tsym=USD&limit=120" #&aggregate=3&e=CCCAGG
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

        retval = "[" + ",".join(series1) + "]~["   + ",".join(series2) + "]"
        caches = [{
            "symbol": lookup,
            "data": retval
        }]
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




@app.route('/Gethistoricaldata_NoCache/<symbol>')
def GetHistoricalDataFromCryptoCompare(symbol=None):
    namevalue = []
    struri = "https://min-api.cryptocompare.com/data/histoday?fsym=" + symbol + "&tsym=USD&limit=100" #&aggregate=3&e=CCCAGG
    response = requests.get(struri)
    clist = response.json()['Data']
    df = pd.DataFrame(clist)
    dfnew = df[['time','close']]
    for index,  row in dfnew.iterrows():
        hdate = datetime.fromtimestamp(int(row['time'])).strftime('%m/%d/%Y')
        hts =  int(time.mktime(datetime.strptime(hdate,'%m/%d/%Y').timetuple()))*1000
        namevalue.append("[" + str(hts) + "," + str(row['close']) + "]")
    retval = "[" +  ",".join(namevalue) + "]"
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
        dfnew = dfLog[['Time', 'Ticker', 'Symbol', 'Qty', 'Type', 'Price', 'Cost', 'NetCash', 'mult']]
    else:
        dfnew = pd.DataFrame(
            columns=['Time', 'Ticker', 'Symbol', 'Qty', 'Type', 'Price', 'Cost', 'NetCash', 'mult'])
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
                 "mult":sign
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
    #host = socket.gethostbyname(socket.gethostname())
    #host = socket.gethostbyname("")
    #client = MongoClient(host, 27017)
    client = MongoClient('mongodb://mongo:27017')
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

def GetPL():
    df = pd.DataFrame(np.empty(0, dtype=[('Ticker','S20'),
                                         ('Position', 'f8'),
                                         ('MktPrice', 'f8'),
                                         ('Value', 'f8'),
                                         ('WAP', 'f8'),
                                         ('UPL', 'f8'),
                                         ('RPL', 'f8'),
                                         ('TotalPL', 'f8'),
                                         ('PerByShare', 'f8'),
                                         ('PerByDollar', 'f8')
                                         ]
                               ))
    dflog = GetTradeLog()
    cash2invest = GetInvestableCash()
    if len(dflog) > 0:

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
             df.loc[df['Ticker'] == ticker, 'UPL'] = 0
             df.loc[df['Ticker'] == ticker, 'RPL'] = 0

        for ticker in dfqty.index:
            df.loc[df['Ticker'] == ticker, 'Position'] =  dfqty.loc[ticker]

        cashlevel = float(GetCashLevel())
        TotalPos = df['Position'].sum() - cashlevel
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
                if (row['Ticker'].upper() != "CASH"):
                    df.loc[df['Ticker'] == row['Ticker'], 'PerByShare'] = (position / TotalPos) * 100
                else:
                    df.loc[df['Ticker'] == row['Ticker'], 'PerByShare'] = 0

            sumofsharessold = dflog[(dflog.Type == 'S') & (dflog.Ticker==row['Ticker'])]["Qty"].sum()
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
            dfnew =df[['Ticker','Position','MktPrice','Value','WAP','UPL', 'RPL', 'TotalPL', 'PerByShare', 'PerByDollar']]
    else:
        dfnew = df
    return dfnew


if __name__ == "__main__":
    app.run(debug=False,host='0.0.0.0')
    #app.run(debug=True,threaded=True)
