import pandas as pd
from dash import Dash, html, dcc
from utils.query_mongoDB_functions import *
from apps.backtest import *

# database connection
url = "mongodb+srv://foscoa:Lsw0r4KyI0rlq8YH@cluster0.vu31vch.mongodb.net/"
client = pymongo.MongoClient(url)

# pull ETFs data ---------------------------------------------------------------------------------------------------

db = client.ETFs
collection = db.Yahoo_Finance

start = '2014-01-02'
end = '2024-03-31'
tickers = ['SPY', '^VIX']
param = "Open"

ETFs = q_TS_ETFs(tickers=tickers,
               start=start,
               end=end,
               param=param,
               collection=collection)


# pull VIX futures ETFs data ---------------------------------------------------------------------------------------

db = client.Listed_Futures
collection = db.CBOE_VIX_Futures_monthly

start = '2013-01-02'
end = '2024-03-31'

# Project only the "Open" and "Date" fields
projection = {"_id": 0, "Futures": 1, 'Expiry': 1}

# Execute the query
futures_map = pd.DataFrame(list(collection.find({}, projection))).drop_duplicates().sort_values(by='Expiry')

contracts = list(futures_map.Futures)

# Open
param = 'Open'

open = q_TS_VIX_futures(contracts=contracts,
                      start=start,
                      end=end,
                      param=param,
                      collection=collection)

open = open[list(futures_map.Futures)] # order by maturity

# Open
param = 'Expiry'

expiry = q_TS_VIX_futures(contracts=contracts,
                        start=start,
                        end=end,
                        param=param,
                        collection=collection)

expiry = expiry[[fut for fut in list(futures_map.Futures) if fut in expiry.columns]]  # order by maturity
expiry.columns = expiry.columns + '_exp'

# pull VIX futures interpolated term structure ---------------------------------------------------------------------

param = 'Open'

db = client.Listed_Futures
collection = db.CBOE_VIX_Futures_monthly_INT
vix_int = q_TS_VIX_futures_INT(start=start,
                           end=end,
                           param=param,
                           collection=collection)




# Strategy -------------------------------------------------------------------------------------------------------------

starting_capital = 100000
pct_risk = 0.7
allocation =starting_capital*pct_risk

delta_days = expiry.apply(lambda col: col - expiry.index)

def  calc_weights(x):
    w = 1 - np.abs((x-pd.Timedelta(days=31)))/np.abs((x.dropna()[0:2]-pd.Timedelta(days=31))).sum()
    return w

weights = delta_days.apply(calc_weights, axis=1)


# quantity in SVXY
data['q_SVXY'] = (allocation/data.SVXY).astype(int)*(data.month_1-data.VIX > 0).astype(int)

# quantity in VIXY
data['q_VIXY'] = (0.5*allocation/data.VIXY).astype(int)*(data.month_1-data.VIX < 0).astype(int)

# PnL - the definition is: PnL = market value at opening (t+1) - market value at opening (t)
data['LSV_PnL'] = (data.SVXY.shift(-1) - data.SVXY)*data.q_SVXY + (data.VIXY.shift(-1) - data.VIXY)*data.q_VIXY
data['LSV_PnL'] = data['LSV_PnL'].fillna(0)

# initialize variables
asset_prices = data[['VIXY', 'SVXY']]
signal = data[['q_VIXY', 'q_SVXY']]
signal.columns = ['VIXY', 'SVXY']
benchmark = data.SPY

# initialize apps istance
strategy = BacktestTradingStrategy(
    name='LSV unhedged',
    description='The strategy goes long in SVXY if a positive basis exists between the VIX and the 1-month '
                'interpolated VIX value',
    asset_prices=asset_prices,
    benchmark=benchmark,
    signal=signal,
    starting_capital=starting_capital
)

# apps app ---------------------------------------------------------------------------------------------------------

app = Dash(__name__)

# app
app.layout = html.Div(
    children=[

        html.Div(
            children=[
                dcc.Graph(
                    id='example-graph',
                    figure=strategy.generate_report(),
                    style= {'height': '70vh'}
                ),
            ],
            style={'height': '70vh'}
        ),

        html.Div(
            children=[
                strategy.generate_dash_monthly_returns_table()
            ],
            style={'marginLeft': 80, 'marginRight': 120}
        ),

])

if __name__ == '__main__':
    app.run_server(debug=False, port=5001)






