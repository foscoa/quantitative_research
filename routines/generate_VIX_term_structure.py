import numpy as np
from scipy import interpolate
from utils.query_mongoDB_functions import *
from datetime import datetime, timedelta

url = "mongodb+srv://foscoa:Lsw0r4KyI0rlq8YH@cluster0.vu31vch.mongodb.net/"
client = pymongo.MongoClient(url)

# Check latest database entries
latest_date_CBOE_VIX_Futures_monthly_INT = client.Listed_Futures.CBOE_VIX_Futures_monthly_INT.\
    find_one({}, sort=[("Date", -1)])['Date']
latest_date_VIX_index = client.ETFs.Yahoo_Finance.\
    find_one({'Ticker': '^VIX'}, sort=[("Date", -1)])['Date']
latest_date_CBOE_VIX_Futures_monthly = client.Listed_Futures.CBOE_VIX_Futures_monthly.\
    find_one({}, sort=[("Trade Date", -1)])['Trade Date']

# initialize dates
start_date = latest_date_CBOE_VIX_Futures_monthly_INT + timedelta(days=1)
end_date = min(latest_date_VIX_index, latest_date_CBOE_VIX_Futures_monthly) + timedelta(days=1)

start_date = start_date.strftime('%Y-%m-%d')
end_date = end_date.strftime('%Y-%m-%d')


if start_date < end_date:

    # QUERY VIX index ----
    db = client['ETFs']
    collection = db['Yahoo_Finance']
    tickers = ['^VIX']
    param = "Open"

    vix_index = q_TS_ETFs(tickers=tickers,
                   start=start_date,
                   end=end_date,
                   param=param,
                   collection=collection)

    # QUERY VIX futures ----
    db = client.Listed_Futures
    collection = db.CBOE_VIX_Futures_monthly

    # Project
    projection = {"_id": 0, "Futures": 1, 'Expiry': 1}

    # Execute the query
    futures_map = pd.DataFrame(list(collection.find({}, projection))).drop_duplicates().sort_values(by='Expiry')
    contracts = list(futures_map.Futures)

    # Total Volume
    tot_vol = q_TS_VIX_futures(contracts=contracts,
                              start=start_date,
                              end=end_date,
                              param='Total Volume',
                              collection=collection)

    tot_vol = tot_vol[list(futures_map.Futures)] # order by maturity

    # Open
    params = ['Open', 'High', 'Close', 'Low']

    open = q_TS_VIX_futures(contracts=contracts,
                          start=start_date,
                          end=end_date,
                          param=param,
                          collection=collection)

    open = open[list(futures_map.Futures)] # order by maturity

    # Close
    param = 'Close'

    close = q_TS_VIX_futures(contracts=contracts,
                          start=start_date,
                          end=end_date,
                          param=param,
                          collection=collection)

    close = close[list(futures_map.Futures)] # order by maturity

    # building the VIX term structure --------------------------------------------------------------------------------------

    VIX_list = list()
    dates_open = [today for today in open.index[open.index >= vix_index.index[0]] if today in vix_index.index]

    # iterate on each date
    for today in dates_open:
        # select values and volume for the day
        open_i = open[open.index == today]
        vol_i = tot_vol[tot_vol.index == today]
        today_vix = vix_index[vix_index.index == today]['VIX'].values[0]

        # select only contract with volumne > 0
        contracts_pos_volume = list(vol_i.columns[(vol_i > 0).values[0]])
        today_open = [open_i[ct].values[0] for ct in contracts_pos_volume]

        today_expiries = [futures_map[futures_map.Futures == ct]['Expiry'].values[0] for ct in contracts_pos_volume]
        tte = [exp-today for exp in today_expiries] # tte = time to expiry

        # check if today the first contract is expiring. If yes, use VIX number and not the future
        if today.to_datetime64() == today_expiries[0]:
            x_array = today_expiries
            y_array = [today_vix] + today_open[1:]
        else:
            x_array = [today.to_datetime64()] + today_expiries
            y_array = [today_vix] + today_open

        # cublic spline
        x = np.array(x_array)
        y = np.array(y_array)
        cs = interpolate.CubicSpline(x, y)

        # generate grid array
        interpol_dt = today.to_datetime64() + [np.timedelta64((k+1)*30, 'D') for k in np.arange(8)]

        count = 1
        for date in interpol_dt:

            dict = {
                "Point": "month " + str(count),
                "Interpolation Date": datetime.utcfromtimestamp(date.astype('int64') * 1e-9),
                "Date": today.to_pydatetime(),
                "Open": cs(date).tolist(),
                "Open_nu1": cs(date, nu=1)*1e+15
            }

            VIX_list.append(dict)
            count += 1

        print("Curve " + today.strftime("%Y-%m-%d") + " successfully uploaded")

    # save data in MongoDB
    db = client.Listed_Futures
    collection = db.CBOE_VIX_Futures_monthly_INT
    collection.insert_many(VIX_list)
else:
    print("Database -CBOE_VIX_Futures_monthly_INT- is up do date")