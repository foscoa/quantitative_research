import pandas as pd
from utils.query_mongoDB_functions import *
import plotly.io as pio
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# display plot on the browser
pio.renderers.default = "browser"

# database connection
url = "mongodb+srv://foscoa:Lsw0r4KyI0rlq8YH@cluster0.vu31vch.mongodb.net/"
client = pymongo.MongoClient(url)


def pull_liquidity_data(client, start, end):
    # pull VIX futures data ---------------------------------------------------------------------------------------
    db = client.Listed_Futures
    collection = db.CBOE_VIX_Futures_monthly

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

    tot_vol = tot_vol[[fut for fut in list(futures_map.Futures) if fut in tot_vol.columns]]  # order by maturity

    # Expiry
    param = 'Expiry'

    expiry = q_TS_VIX_futures(contracts=contracts,
                            start=start,
                            end=end,
                            param=param,
                            collection=collection)

    expiry = expiry[[fut for fut in list(futures_map.Futures) if fut in expiry.columns]]  # order by maturity

    # calculate days left to expiration
    days_left = expiry.apply(lambda column: (column - column.index))

    # save days left and
    liquidity = [
        [days_left[i].loc[j].days, tot_vol[i].loc[j]]
        for i in tot_vol.columns
        for j in tot_vol.index
        if not pd.isna(days_left[i].loc[j])
    ]

    liquidity = pd.DataFrame(liquidity, columns=['DTM', 'Volume']) # create dataframe
    liquidity = liquidity[liquidity.DTM != 0] # contracts maturing in the same day
    liquidity = liquidity.groupby(['DTM']).median() # calculate median
    liquidity['Days to Expiry'] = liquidity.index
    liquidity.rename(columns={'Volume': 'Median Volume'}, inplace=True) # enaming volume column

    return liquidity

# Scatter plot with Plotly Express
end = '2024-03-31'

liquidity = pull_liquidity_data(client=client, start='2013-01-01', end=end)
fig1 = px.scatter(liquidity,
                 x='Days to Expiry',
                 y='Median Volume',
                 title='Median volume for given days to expiry')
period1 = '2013-01-01' + ' / ' + end

liquidity = pull_liquidity_data(client=client, start='2020-01-01', end=end)
fig2 = px.scatter(liquidity,
                 x='Days to Expiry',
                 y='Median Volume',
                 title='Median volume for given days to expiry')
period2 = '2020-01-01' + ' / ' + end

# Create a subplot
fig = make_subplots(rows=2, cols=1, subplot_titles=(period1, period2))

# Add traces from fig1 to the first subplot
for trace in fig1.data:
    fig.add_trace(trace, row=1, col=1)

# Add traces from fig2 to the second subplot
for trace in fig2.data:
    fig.add_trace(trace, row=2, col=1)


# Set axis limits for the first subplot
fig.update_yaxes(range=[0, 120000], row=1, col=1)  # Set y-axis limit
fig.update_yaxes(range=[0, 120000], row=2, col=1)    # Set y-axis limit


# Save the figure
out_dir = "C:\\Users\\Fosco\\Desktop\\quantitative_research\\ad_hoc_research\\VIX_futures_liquidity_analysis\\"

# fig.write_image(out_dir + "VX_liquidity.eps", width=1920, height=1080)

