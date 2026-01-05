import pandas as pd
import datetime as dt
import numpy as np
import pytz
import yfinance as yf
import matplotlib.pyplot as plt

def stock_name (ticker):
    ticker_obj = yf.Ticker(ticker)
    return ticker_obj.info["longName"]

def valid_ticker(ticker: str) -> bool:
    ticker_obj = yf.Ticker(ticker.upper())
    test= ticker_obj.history(period="1d")
    try:
        return not test.empty
    except Exception:
        return False

def ask_ticker():
    while True:
        ticker = input("Enter the ticker symbol: ")
        if valid_ticker(ticker):
            return ticker.upper()
        else:
            print("Invalid ticker symbol please try again")

def ask_number ():
    while True:
        try:
            return int(input("Enter the number:"))
        except ValueError:
            print("Invalid number please try again")


stocks=[]
print("Enter first the ticker symbol of the stock you want to analyze")
stocks.append(ask_ticker())
print("Enter the number of stocks you want to compare with your company: ")
number_of_stocks= int(ask_number())

for i in range(number_of_stocks):
    stocks.append(ask_ticker())

print("Number of days you want to look at: ")
dd=int(ask_number())
enddate=dt.datetime.now(tz=pytz.timezone('America/Chicago'))
startdate= enddate-dt.timedelta(days=3*365)


#Stocks price and return analysis

df_gap=yf.download(stocks,start=startdate,end=enddate, auto_adjust=True)

df_linear= df_gap.ffill()
adj_close_price= df_linear["Close"]
days_requested= adj_close_price.tail(dd)
normalized=((days_requested/days_requested.iloc[0])-1)*100

fifty_days= df_linear["Close"].rolling(window=50).mean()        #chart with stock price and 50 - 200 moving avarage
twohundred_days= df_linear["Close"].rolling(window=200).mean()

Moving_avg= pd.DataFrame ({
    "Close price": adj_close_price[stocks[0]],
    "MA50": fifty_days[stocks[0]],
    "MA200": twohundred_days[stocks[0]]
})
Moving_avg= Moving_avg.dropna()


normalized.plot(title= stock_name(stocks[0]) + " return vs Peers", figsize=(10,6))  #CORRETTO
plt.ylabel('Δ%')
Moving_avg.tail(dd).plot(title= stock_name(stocks[0]) + " Stock Chart", figsize=(10,6))
plt.ylabel("Price")


#download stocks data
Stocks_data= []
for i in range(len(stocks)):
    Stocks_data.append(yf.Ticker(stocks[i]))


#download share outstanding number
shares_dict= {}
for stock in Stocks_data:
    shares= stock.get_shares_full()
    shares.index= shares.index.date
    shares=shares.groupby(shares.index).last()
    shares_dict[stock.ticker]= shares

shares_outstanding_history= pd.DataFrame(shares_dict)

#P/E chart

earnings_dict={}       #donwload of net income using quarterly data when avaiable and anual for the remaining part
for stock in Stocks_data:
    income_annual= stock.income_stmt.loc["Net Income"].dropna().sort_index()
    income_annual.index= pd.to_datetime(income_annual.index)
    earnings_annual_daily= income_annual.reindex(shares_outstanding_history.index, method="ffill")

    income_q = stock.quarterly_income_stmt.loc["Net Income"].dropna().sort_index()  #earnings ttm
    income_q.index= pd.to_datetime(income_q.index)
    net_income_ttm = income_q.rolling(4).sum().dropna()
    earnings_daily=net_income_ttm.reindex(shares_outstanding_history.index, method="ffill")

    earnings_final= earnings_annual_daily.copy()

    if not net_income_ttm.empty:
        switching_date= net_income_ttm.index[0]
        earnings_final.index= pd.to_datetime(earnings_final.index)
        switch= earnings_final.index>=switching_date
        earnings_final.loc[switch]=earnings_daily.loc[switch]

    earnings_dict[stock.ticker]= earnings_final

net_income = pd.DataFrame(earnings_dict)

daily_eps= net_income/ shares_outstanding_history
daily_eps=daily_eps.reindex(adj_close_price.index, method="ffill")
P_E= (adj_close_price/daily_eps.ffill().rolling(30, min_periods=5).median()).dropna()

P_E.plot(title= stock_name(stocks[0])+" Trailing P/E history", figsize=(10,6))



#free cash flow per share chart

fcf_dict= {}
for stock in Stocks_data:
    free_cash_flow_ttm= stock.quarterly_cashflow.loc["Free Cash Flow"].dropna().sort_index().rolling(4).sum().dropna()
    fcf_ttm_daily= free_cash_flow_ttm.reindex(shares_outstanding_history.index, method="ffill")
    fcf_dict [stock.ticker]= fcf_ttm_daily

free_cash_flow_daily= pd.DataFrame(fcf_dict)

cash_per_share = (free_cash_flow_daily / shares_outstanding_history).dropna()
cash_per_share.plot(title=stock_name(stocks[0])+ " Free Cash Flow per share", figsize=(10,6))



#total asset turnover chart
total_asset= Stocks_data[0].balance_sheet.loc["Total Assets"].dropna()
revenues=Stocks_data[0].financials.loc["Total Revenue"].dropna()
total_asset_turnover= revenues/total_asset
revenues_pct=revenues.pct_change()*100
dates=total_asset_turnover.index

fig, ax1 = plt.subplots(figsize= (9,5))
ax1.plot(dates, total_asset_turnover , 'b-o', label="TAT")
ax1.set_xlabel('Years')
ax1.set_ylabel('Total Asset Turnover')
ax2 = ax1.twinx()
ax2.plot(dates, revenues_pct, 'y-o', label="revenue % change")
ax2.set_ylabel('Revenue % YoY change')
ax1.legend(loc='lower left')
ax2.legend(loc='upper left')
plt.title( stock_name(stocks[0]) + " total asset turnover" )


#income statment ratios charts
Net_profit_margin_dict= {}
ebitda_margin_dict= {}
for stock in Stocks_data:
    net_income= stock.income_stmt.loc["Net Income"].dropna()
    ebitda= stock.income_stmt.loc["EBITDA"].dropna()
    revenues= stock.income_stmt.loc["Total Revenue"].dropna()
    Net_profit_margin_dict[stock.ticker]= (net_income/revenues)*100
    ebitda_margin_dict[stock.ticker]=(ebitda/revenues)*100

Net_profit_margin= pd.DataFrame(Net_profit_margin_dict)
ebitda_margin= pd.DataFrame(ebitda_margin_dict)

Net_profit_margin.groupby(Net_profit_margin.index.year).last().plot(title=stock_name(stocks[0])+ " Net Income Margin vs peers",marker='o', figsize=(10,6))
plt.ylabel('Δ%')
ebitda_margin.groupby(ebitda_margin.index.year).last().plot(title=stock_name(stocks[0])+ " Ebitda margin vs peers",marker='o', figsize=(10,6))
plt.ylabel('Δ%')




#Roe and leverage chart

book_equity= Stocks_data[0].balance_sheet.loc["Stockholders Equity"].dropna().sort_index()
book_equity_mean= book_equity.rolling(2).mean()
leverage= (total_asset/book_equity_mean).dropna()

roe= ((leverage* total_asset_turnover*(Net_profit_margin[stocks[0]]/100))*100).dropna()
dates_roe= roe.index

fig, ax1 = plt.subplots(figsize=(10,6))
ax1.plot(dates_roe, roe, 'g-o', label="roe" )
ax1.set_xlabel('Years')
ax1.set_ylabel('Roe %')
ax2 = ax1.twinx()
ax2.plot(dates_roe, leverage, 'y-o', label="leverage" )
ax2.set_ylabel('Leverage')
ax1.legend(loc='lower left')
ax2.legend(loc='upper left')
plt.title(stock_name(stocks[0])+ " return on equity")

plt.show()

