import pymongo
from datetime import datetime
import pandas as pd
import numpy as np
from scipy import interpolate
import matplotlib.pyplot as plt
from utils.query_mongoDB_functions import *
import plotly.graph_objs as go

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
for today in open.index[open.index >= ts.index[0]]:
    if today in ts.index:
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

        # plot
        fig, ax = plt.subplots(figsize=(6.5, 4))
        ax.plot(x, y, 'o', label='data')
        ax.plot(dt, cs(dt), label="S")
        ax.plot(interpol_dt, cs(interpol_dt), 'o', label="interpol")
        plt.show()


        trace2 = go.Scatter(
            x=x,
            y=y,
            mode='markers',
            name='Traded Contracts',
            marker=dict(size=12,
                        color='darkred'),
        )
        trace1 = go.Scatter(
            x=dt,
            y=cs(dt),
            mode='lines',
            name='Fit',
            opacity=0.5
        )

        trace3 = go.Scatter(
            x=interpol_dt,
            y=cs(interpol_dt),
            mode='markers',
            name='Interpolated Points',
            marker=dict(size=12,
                        symbol='square-open',
                        color='midnightblue'),
        )

        data = [trace1, trace2, trace3]

        fig = go.Figure(data=data)
        fig.show()



        count = 1
        for date in interpol_dt[1:]:

            dict = {
                "Point": "month " + str(count),
                "Date Iterpolation": datetime.utcfromtimestamp(date.astype('int64') * 1e-9),
                "Date": datetime.utcfromtimestamp(today.to_datetime64().astype('int64') * 1e-9),
                "Open": cs(date).tolist()
            }

            # # insert in database
            # collection.insert_one(dict)
            #

            VIX_list.append(dict)
            count += 1

        print("Curve " + today.strftime("%Y-%m-%d") + " successfully uploaded")


db = client.Listed_Futures
collection = db.CBOE_VIX_Futures_monthly_INT
collection.insert_many(VIX_list)