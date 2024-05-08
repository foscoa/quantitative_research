import sys
sys.path.extend(['C:\\Users\\Fosco\\Desktop\\quantitative_research'])

from datetime import date, timedelta
import numpy as np
from scipy import interpolate
from utils.query_mongoDB_functions import *
import plotly.graph_objs as go
from dash import Dash, html, dcc, Input, Output, callback

def query_dates(client):
    # find all common dates between yahoo and CBOE
    dates_CBOE = pd.DataFrame(list(
        client.Listed_Futures.CBOE_VIX_Futures_monthly.find({}, {"_id": 0, "Trade Date": 1}))
    ).drop_duplicates()
    dates_CBOE = list(dates_CBOE['Trade Date'])

    dates_vix = pd.DataFrame(list(
        client.ETFs.Yahoo_Finance.find({'Ticker': '^VIX'}, {"_id": 0, "Date": 1}))
    ).drop_duplicates()
    dates_vix = list(dates_vix['Date'])

    return [date for date in dates_CBOE if date in dates_vix]

def generate_plot_VIX_term_structure(date, param, client):

    # QUERY VIXs -------------------------------------------------------------------------------------------------------
    vix = q_TS_ETFs(tickers=['^VIX'],
                    start=date,
                    end=date,
                    param=param,
                    collection=client.ETFs.Yahoo_Finance)

    # QUERY VIX Futures ------------------------------------------------------------------------------------------------

    # Find all contracts sorted by maturity
    projection = {"_id": 0, "Futures": 1, 'Expiry': 1}

    # Execute the query
    futures_map = pd.DataFrame(list(client.Listed_Futures.CBOE_VIX_Futures_monthly.find({}, projection))
                               ).drop_duplicates().sort_values(by='Expiry')

    contracts = list(futures_map.Futures)

    # Total volume
    tot_vol = q_TS_VIX_futures(contracts=contracts,
                               start=date,
                               end=date,
                               param='Total Volume',
                               collection=client.Listed_Futures.CBOE_VIX_Futures_monthly)


    tot_vol = tot_vol[[fut for fut in contracts if fut in tot_vol.columns]] # order by maturity

    # VIX price
    vix_price = q_TS_VIX_futures(contracts=contracts,
                                 start=date,
                                 end=date,
                                 param=param,
                                 collection=client.Listed_Futures.CBOE_VIX_Futures_monthly)

    vix_price = vix_price[[fut for fut in contracts if fut in vix_price.columns]] # order by maturity


    # building the VIX term structure

    today_contracts = list(tot_vol.columns[(tot_vol > 0).values[0]])
    today_expiries = [futures_map[futures_map.Futures == ct]['Expiry'].values[0] for ct in today_contracts]
    today_expiries[0] = today_expiries[0] + 1*10**9*60*60*5 # to avoid problems if first contract expires today
    today_prices = list(vix_price.values[0])
    tte = [exp-np.datetime64(date) for exp in today_expiries]
    today_vix = vix.values[0][0]

    # cublic spline
    date_long_format = np.datetime64(date+ 'T00:00:00.000000000')
    x = np.array([date_long_format] + today_expiries)
    y = np.array([today_vix] + today_prices)
    cs = interpolate.CubicSpline(x, y)

    dt = date_long_format + [np.timedelta64(k, 'D') for k in np.arange(int((tte / np.timedelta64(1, 'D'))[-1]))]
    interpol_dt = date_long_format + [np.timedelta64((k + 1) * 30, 'D') for k in np.arange(8)]

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
        x=np.array([date_long_format]),
        y=np.array([today_vix]),
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
              + "as of " + date + ". "
              + "Source: " + param +
              " </sub>" +

              "<br>",

    )

    return fig

def validate(date_text):
    try:
        if date_text != datetime.strptime(date_text, "%Y-%m-%d").strftime('%Y-%m-%d'):
            raise ValueError
        return True
    except ValueError:
        return False

# database connection
url = "mongodb+srv://foscoa:Lsw0r4KyI0rlq8YH@cluster0.vu31vch.mongodb.net/"
client = pymongo.MongoClient(url)


# Generate complete list of dates
dates = query_dates(client=client)
date_compl = [np.min(dates) + timedelta(days=i) for i in range((np.max(dates) - np.min(dates)).days + 1)]

# choose parameter
param = "Open"

# date = '2022-03-16'
#
#
# fig = generate_plot_VIX_term_structure(date=date,
#                                        param=param,
#                                        client=client)
# fig.show()

# APP -----------------
app = Dash(__name__)

app.layout = html.Div([
    html.Br(),
    dcc.DatePickerSingle(
        id='my-date-picker-single',
        min_date_allowed=np.min(dates),
        max_date_allowed=np.max(dates),
        date=np.max(dates),
        disabled_days=[date for date in date_compl if date not in dates]
    ),
    html.Br(),
    html.Div(
            children=[
                dcc.Graph(
                    id='example-graph',
                    style= {'height': '85vh'}
                ),
            ])
])

@callback(
    Output('example-graph', 'figure'),
    Input('my-date-picker-single', 'date'))
def update_output(date_value):
    if (date_value is not None):
        if(validate(date_value)):
            print(date_value)
            return generate_plot_VIX_term_structure(date=date_value.split('T')[0],
                                                param=param,
                                                client=client)
        else:
            return go.Figure()
    else:
        return go.Figure()

if __name__ == '__main__':
    app.run_server(debug=False, port=5002)

