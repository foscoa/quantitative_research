import pandas as pd
from utils.query_mongoDB_functions import *
import plotly.express as px

# database connection
url = "mongodb+srv://foscoa:Lsw0r4KyI0rlq8YH@cluster0.vu31vch.mongodb.net/"
client = pymongo.MongoClient(url)

# pull VIX futures data ---------------------------------------------------------------------------------------

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

tot_vol = tot_vol[list(futures_map.Futures)]  # order by maturity

# Expiry
param = 'Expiry'

expiry = q_TS_VIX_futures(contracts=contracts,
                        start=start,
                        end=end,
                        param=param,
                        collection=collection)

expiry = expiry[list(futures_map.Futures)]  # order by maturity

# calculate days left to expiration
days_left = expiry.apply(lambda column: (column - column.index).days)

empty_list = list()
for i in tot_vol.columns:
    for j in tot_vol.index:
        if not pd.isna(days_left[i].loc[j]):
            empty_list.append([days_left[i].loc[j].days, tot_vol[i].loc[j]])


liquidity = pd.DataFrame(empty_list, columns=['DTM', 'Volume'])

liquidity = liquidity[liquidity.DTM != 0] # remove DTM = 0

liquidity = liquidity.groupby(['DTM']).median()

liquidity['Days to Expiry'] = liquidity.index

# Renaming a single column
liquidity.rename(columns={'Volume': 'Median Volume'}, inplace=True)


# Scatter plot with Plotly Express
fig = px.scatter(liquidity,
                 x='Days to Expiry',
                 y='Median Volume',
                 title='Median volume for given days to expiry')

# Show the plot
fig.show()
