
from dash import Dash, html, dcc
from utils.query_mongoDB_functions import *
from backtest.backtest import *

# database connection
url = "mongodb+srv://foscoa:Lsw0r4KyI0rlq8YH@cluster0.vu31vch.mongodb.net/"
client = pymongo.MongoClient(url)
def pull_data():

    # pull ETFs data ---------------------------------------------------------------------------------------------------

    db = client.ETFs
    collection = db.Yahoo_Finance

    start = '2014-01-02'
    end = '2024-03-31'
    tickers = ['SPY', 'VIXY', 'SVXY', '^VIX']
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

    # Total Volume
    tot_vol = q_TS_VIX_futures(contracts=contracts,
                          start=start,
                          end=end,
                          param='Total Volume',
                          collection=collection)

    tot_vol = tot_vol[list(futures_map.Futures)] # order by maturity

    # Open
    param = 'Open'

    open = q_TS_VIX_futures(contracts=contracts,
                          start=start,
                          end=end,
                          param=param,
                          collection=collection)

    open = open[list(futures_map.Futures)] # order by maturity


    # pull VIX futures interpolated term structure ---------------------------------------------------------------------

    db = client.Listed_Futures
    collection = db.CBOE_VIX_Futures_monthly_INT
    vix_int = q_TS_VIX_futures_INT(start=start,
                               end=end,
                               param=param,
                               collection=collection)

    # pull VIX futures interpolated term structure ---------------------------------------------------------------------

    db = client.Listed_Futures
    collection = db.CBOE_VIX_Futures_monthly_INT
    vix_int_nu1 = q_TS_VIX_futures_INT(start=start,
                               end=end,
                               param="Open_nu1",
                               collection=collection)


    # merging data -----------------------------------------------------------------------------------------------------

    vix_int_tot = pd.merge(vix_int, vix_int_nu1, left_index=True, right_index=True, how='left')
    data = pd.merge(ETFs, vix_int_tot, left_index=True, right_index=True, how='left')
    data.columns = data.columns.str.replace(" ", "_").to_list()

    return data

# pull data ------------------------------------------------------------------------------------------------------------
data = pull_data()

# Strategy -------------------------------------------------------------------------------------------------------------

starting_capital = 100000
pct_risk = 0.7
allocation =starting_capital*pct_risk

# quantity in SVXY
data['q_SVXY'] = (allocation/data.SVXY).astype(int)*(data.month_1-data.VIX > 2).astype(int)

# quantity in VIXY
data['q_VIXY'] = (allocation/data.VIXY).astype(int)*(data.month_1-data.VIX < 0).astype(int)

# PnL
data['LSV_PnL'] = (data.SVXY.shift(-1) - data.SVXY)*data.q_SVXY + (data.VIXY.shift(-1) - data.VIXY)*data.q_VIXY
data['LSV_PnL'] = data['LSV_PnL'].fillna(0)

# initialize variables
asset_prices = data[['VIXY', 'SVXY']]
signal = data[['q_VIXY', 'q_SVXY']]
signal.columns = ['VIXY', 'SVXY']
benchmark = data.SPY

# Define Strategy instance
strategy = BacktestTradingStrategy(
    name='LSV',
    description='Long-Short VIX',
    asset_prices=asset_prices,
    benchmark=benchmark,
    signal=signal,
    starting_capital=starting_capital
)

# backtest app ---------------------------------------------------------------------------------------------------------

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






