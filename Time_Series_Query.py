import pymongo
from datetime import datetime
import pandas as pd

url = "mongodb+srv://foscoa:Lsw0r4KyI0rlq8YH@cluster0.vu31vch.mongodb.net/"

client = pymongo.MongoClient(url)
db = client['ETFs']
collection = db['Yahoo_Finance']

print(client.list_database_names())

start = '2014-01-01'
end = '2024-03-31'
tickers = ['SPY', 'VIXY', 'SVXY', '^VIX']
param = "Open"

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
        projection = {"_id": 0, "Open": 1, "Date": 1}

        # Execute the query
        cursor = collection.find(query, projection).sort("Date", pymongo.ASCENDING)

        # Iterate over the cursor to get params and corresponding dates
        opening_prices = []
        dates = []
        for document in cursor:
            opening_prices.append(document["Open"])
            dates.append(document["Date"])

        data_to_return = pd.merge(data_to_return,
                            pd.DataFrame(data=opening_prices, index=dates),
                            left_index=True, right_index=True, how='outer')

    data_to_return.columns = [tck.replace('^', '') for tck in tickers]

    return data_to_return


ts = q_TS_ETFs(tickers=tickers,
               start=start,
               end=end,
               param=param,
               collection=collection)