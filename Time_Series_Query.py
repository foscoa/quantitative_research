import pymongo
from datetime import datetime
import pandas as pd
import numpy as np
from scipy import interpolate
import matplotlib.pyplot as plt

url = "mongodb+srv://foscoa:Lsw0r4KyI0rlq8YH@cluster0.vu31vch.mongodb.net/"

client = pymongo.MongoClient(url)

def q_TS_ETFs(tickers, start, end, param, collection):

    # Define start and end dates in datetime format
    start_date = datetime.strptime(start, "%Y-%m-%d")  # start date
    end_date = datetime.strptime(end, "%Y-%m-%d")  # end date

    # Initialize empty df to return
    data_to_return = pd.DataFrame()

    # loop on all tickers
    for tck in tickers:

        # Define the query to retrieve opening prices within the specified date range
        query = {
            "Date": {"$gte": start_date, "$lte": end_date},  # Filter documents by date range
            param: {"$exists": True},  # Filter documents that have the "Open" field
            "Ticker": tck
        }

        # Project only the "Open" and "Date" fields
        projection = {"_id": 0, param: 1, "Date": 1}

        # Execute the query
        cursor = collection.find(query, projection).sort("Date", pymongo.ASCENDING)

        # Iterate over the cursor to get params and corresponding dates
        opening_prices = []
        dates = []
        for document in cursor:
            opening_prices.append(document[param])
            dates.append(document["Date"])

        data_to_return = pd.merge(data_to_return,
                            pd.DataFrame(data=opening_prices, index=dates),
                            left_index=True, right_index=True, how='outer')

    data_to_return.columns = [tck.replace('^', '') for tck in tickers]

    return data_to_return

def q_TS_VIX_futures(contracts, start, end, param, collection):

    # Define start and end dates in datetime format
    start_date = datetime.strptime(start, "%Y-%m-%d")  # start date
    end_date = datetime.strptime(end, "%Y-%m-%d")  # end date

    # Define the query to retrieve opening prices within the specified date range
    query = {
        "Trade Date": {"$gte": start_date, "$lte": end_date},  # Filter documents by date range
        param: {"$exists": True},  # Filter documents that have the "Open" field
        "Futures": {"$in": contracts}
    }

    # Project only the "Open" and "Date" fields
    projection = {"_id": 0, param: 1, "Trade Date": 1, 'Futures': 1}

    # Execute the query
    cursor = collection.find(query, projection)

    # Create DataFrame
    df = pd.DataFrame(list(cursor))

    # Set 'Trade Date' as index
    df.set_index('Trade Date', inplace=True)

    # Pivot DataFrame to have 'Futures' as columns
    data_to_return = df.pivot(columns='Futures', values=param)

    # fill nan with 0
    data_to_return.fillna(value=0, inplace=True)

    return data_to_return


# QUERY ETFs ----

db = client['ETFs']
collection = db['Yahoo_Finance']

print(client.list_database_names())

start = '2013-01-01'
end = '2024-03-31'
tickers = ['SPY', 'VIXY', 'SVXY', '^VIX']
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

# Volume
param = 'Total Volume'

tot_vol = q_TS_VIX_futures(contracts=contracts,
                      start=start,
                      end=end,
                      param=param,
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

# Close
param = 'Close'

close = q_TS_VIX_futures(contracts=contracts,
                      start=start,
                      end=end,
                      param=param,
                      collection=collection)

close = close[list(futures_map.Futures)] # order by maturity

# building the VIX term structure
idx = 950
today = open.index[idx]
open_i = open[open.index == today]
vol_i=tot_vol[tot_vol.index == today]
today_contracts = list(vol_i.columns[(vol_i > 0).values[0]])
today_expiries = [futures_map[futures_map.Futures == ct]['Expiry'].values[0] for ct in today_contracts]
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

for i in range(len(interpol_dt)):
    print("month " + str(i+1))
    print(interpol_dt[i])
    print(cs(interpol_dt[i]))
