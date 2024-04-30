from datetime import datetime
import pandas as pd
import pymongo

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

def q_TS_VIX_futures_INT(start, end, param, collection):

    # Define start and end dates in datetime format
    start_date = datetime.strptime(start, "%Y-%m-%d")  # start date
    end_date = datetime.strptime(end, "%Y-%m-%d")  # end date

    # Define the query to retrieve opening prices within the specified date range
    query = {
        "Date": {"$gte": start_date, "$lte": end_date},  # Filter documents by date range
        param: {"$exists": True},  # Filter documents that have the "Open" field
    }

    # Project only the "Open" and "Date" fields
    projection = {"_id": 0, param: 1, "Point": 1, "Date": 1}

    # Execute the query
    cursor = collection.find(query, projection)

    # Create DataFrame
    df = pd.DataFrame(list(cursor))

    # Set 'Trade Date' as index
    df.set_index('Date', inplace=True)

    # Pivot DataFrame to have 'Futures' as columns
    data_to_return = df.pivot(columns='Point', values=param)


    return data_to_return
