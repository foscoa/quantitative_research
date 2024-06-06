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
vix_int.columns = vix_int.columns.str.replace(' ', '_')



# Strategy -------------------------------------------------------------------------------------------------------------

starting_capital = 200000
pct_risk = 0.3
allocation =starting_capital*pct_risk
margin_req = 4000
bid_ask = 0.05

delta_days = expiry.apply(lambda col: col - expiry.index)

# Replace '0 and 1' days with NaT for datetime columns
delta_days = delta_days.replace({
    pd.Timedelta('0 days 00:00:00'): pd.NaT,
    pd.Timedelta('1 days 00:00:00'): pd.NaT
})
def  calc_weights(x, days, shift):
    w = 1 - np.abs((x-pd.Timedelta(days=days)))/np.abs((x.dropna()[(shift):(shift+2)]-pd.Timedelta(days=days))).sum()
    return w

weights_mon1 = delta_days.apply(calc_weights, args=[33, 0], axis=1)
weights_mon2 = delta_days.apply(calc_weights, args=[66, 1], axis=1)

# quantity
q_mon1 = ((weights_mon1 > 0)*1*weights_mon1*starting_capital/margin_req*pct_risk).fillna(0).astype(int)*1000
q_mon2 = ((weights_mon2 > 0)*1*weights_mon2*starting_capital/margin_req*pct_risk).fillna(0).astype(int)*1000

# filter dates
q_mon1 = q_mon1[q_mon1.index.isin(ETFs.index)]
q_mon2 = q_mon2[q_mon2.index.isin(ETFs.index)]
open = open[open.index.isin(ETFs.index)]
# q_tot
q_tot = (+q_mon2 - q_mon1).multiply((vix_int.month_1-ETFs.VIX >= 0).astype(int), axis=0) + \
        (-1*q_mon2 + q_mon1).multiply((vix_int.month_1-ETFs.VIX < 0).astype(int), axis=0)

q_tot.columns = open.columns

t_cost = np.abs(q_tot.shift(-1) - q_tot).sum(axis=1)*bid_ask*1

# PnL - the definition is: PnL = market value at opening (t+1) - market value at opening (t)
PnL = (open.shift(-1) - open)*q_tot

# initialize variables
asset_prices = open
signal = q_tot
benchmark = ETFs.SPY

# initialize apps istance
strategy = BacktestTradingStrategy(
    name='LSV unhedged',
    description='The strategy goes long in SVXY if a positive basis exists between the VIX and the 1-month '
                'interpolated VIX value',
    asset_prices=asset_prices,
    benchmark=benchmark,
    signal=signal,
    starting_capital=starting_capital,
    transaction_costs=t_cost
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






