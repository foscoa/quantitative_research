import pymongo
from datetime import date, timedelta
import pandas as pd
import numpy as np
from scipy import interpolate
import matplotlib.pyplot as plt
from utils.query_mongoDB_functions import *
import plotly.graph_objs as go

from dash import Dash, html, dcc, Input, Output, callback

url = "mongodb+srv://foscoa:Lsw0r4KyI0rlq8YH@cluster0.vu31vch.mongodb.net/"
client = pymongo.MongoClient(url)

# QUERY ETFs ----

db = client['ETFs']
collection = db['Yahoo_Finance']


start = '2013-01-01'
end = '2024-03-31'
tickers = ['^VIX']
param = "Open"

ts = q_TS_ETFs(tickers=tickers,
               start=start,
               end=end,
               param=param,
               collection=collection)

# QUERY VIX ----

db = client.Listed_Futures
collection = db.CBOE_VIX_Futures_monthly
start = '2013-01-01'
end = '2024-03-31'

# Project only the "Open" and "Date" fields
projection = {"_id": 0, "Futures": 1, 'Expiry': 1}

# Execute the query
futures_map = pd.DataFrame(list(collection.find({}, projection))).drop_duplicates().sort_values(by='Expiry')

contracts = list(futures_map.Futures)


tot_vol = q_TS_VIX_futures(contracts=contracts,
                      start=start,
                      end=end,
                      param='Total Volume',
                      collection=collection)

tot_vol = tot_vol[list(futures_map.Futures)] # order by maturity

# Open
params = ['Open', 'High', 'Close', 'Low']

open = q_TS_VIX_futures(contracts=contracts,
                      start=start,
                      end=end,
                      param=param,
                      collection=collection)

open = open[list(futures_map.Futures)] # order by maturity

# Close
param = 'Close'

close = q_TS_VIX_futures(contracts=contracts,
                      start=start,
                      end=end,
                      param=param,
                      collection=collection)

close = close[list(futures_map.Futures)] # order by maturity

VIX_list = list()

# building the VIX term structure

today = ts.index[200]

def plot_VIX_term_structure(today):

    open_i = open[open.index == today]
    vol_i=tot_vol[tot_vol.index == today]
    today_contracts = list(vol_i.columns[(vol_i > 0).values[0]])
    today_expiries = [futures_map[futures_map.Futures == ct]['Expiry'].values[0] for ct in today_contracts]
    today_expiries[0] = today_expiries[0] + 1*10**9*60*60*5 # to avoid problems if first contract expires today
    today_open = [open_i[ct].values[0] for ct in today_contracts]
    tte = [exp-today for exp in today_expiries]
    today_vix = ts[ts.index == today]['VIX'].values[0]

    # cublic spline
    x = np.array([today.to_datetime64()] + today_expiries)
    y = np.array([today_vix] + today_open)
    cs = interpolate.CubicSpline(x, y)


    dt = today.to_datetime64() + [np.timedelta64(k, 'D') for k in np.arange(tte[-1].days)]

    interpol_dt = today.to_datetime64() + [np.timedelta64((k+1)*30, 'D') for k in np.arange(8)]


    trace1 = go.Scatter(
        x=dt,
        y=cs(dt),
        mode='lines',
        name='Fit',
        opacity=0.5
    )

    trace2 = go.Scatter(
        x=x,
        y=y,
        mode='markers',
        name='Traded Contracts',
        marker=dict(size=9,
                    symbol='x',
                    color='midnightblue'),
    )

    trace3 = go.Scatter(
        x=interpol_dt,
        y=cs(interpol_dt),
        mode='markers',
        name='Interpolated Point',
        marker=dict(size=12,
                    color='darkred'),
    )

    trace4 = go.Scatter(
        x=[today],
        y=[today_vix],
        mode='markers',
        name='VIX',
        marker=dict(size=12,
                    color='gold'),
    )

    data = [trace1, trace2, trace3, trace4]

    fig = go.Figure(data=data)

    fig.update_layout(
        title="VIX Term Structure" + "<br>"
                      + "<sub>"
                      + "as of " + today.day_name() + ", " + str(today)[0:10] + ". "
                      + "Source: " + "open" +
                      " </sub>" +

                      "<br>",

    )

    return fig

fig = plot_VIX_term_structure(today)


# APP -----------------

dates = [date for date in open.index if date in ts.index]

# Generate complete list of dates
date_compl = [dates[0] + timedelta(days=i) for i in range((dates[-1] - dates[0]).days + 1)]


app = Dash(__name__)

app.layout = html.Div([
    dcc.DatePickerSingle(
        id='my-date-picker-single',
        min_date_allowed=dates[0],
        max_date_allowed=dates[-1],
        date=dates[0],
        disabled_days=[date for date in date_compl if date not in dates]
    ),
    html.Br(),
    html.Div(
            children=[
                dcc.Graph(
                    id='example-graph',
                    figure=fig,
                    style= {'height': '70vh'}
                ),
            ]),
    html.Div(id='output-container-date-picker-single')
])


@callback(
    Output('example-graph', 'figure'),
    Input('my-date-picker-single', 'date'))
def update_output(date_value):
    if date_value is not None:
        return plot_VIX_term_structure(pd.Timestamp(date_value))


if __name__ == '__main__':
    app.run_server(debug=False, port=5002)

