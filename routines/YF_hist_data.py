import pymongo
import yfinance as yf
from utils.store_data_mongoDB_collection import *
from datetime import datetime, timedelta

def download_YF_data(ticker, start_date, end_date):
    try:
        # Download data
        data = yf.download(ticker, start=start_date, end=end_date)
        return data
    except Exception as e:
        print(f"Error downloading data for {ticker}: {e}")
        return None

# Create a mongodb client, use default local host
try:
    client = pymongo.MongoClient("mongodb+srv://foscoa:Lsw0r4KyI0rlq8YH@cluster0.vu31vch.mongodb.net/")
    db = client['ETFs']
    collection = db['Yahoo_Finance']
except Exception:
    print("Error: " + Exception)

ticker_symbol_list = ['SPY', 'SVIX', 'SVXY', 'VIXY', '^VIX'] # Example: Apple Inc.

for ticker_symbol in ticker_symbol_list:
    # Get today's date and subtract 1 day to get yesterday's date
    yesterday = datetime.now() - timedelta(days=1)
    yesterday_date = yesterday.strftime('%Y-%m-%d')
    end_date = yesterday_date

    # Find starting date
    # Query to find the document with the latest Date where Ticker is ticker_symbol
    latest_document = collection.find_one(
        {"Ticker": ticker_symbol},  # Filter by Ticker
        sort=[("Date", -1)]  # Sort by Date in descending order
    )
    if latest_document:
        start_date = latest_document['Date'] + timedelta(days=1)
        start_date = start_date.strftime('%Y-%m-%d')
    else:
        start_date = "2014-01-01"

    # downloading data from Yahoo finance
    if start_date == end_date:
        print("DB is up to date")
    else:
        YF_data = download_YF_data(ticker_symbol, start_date, end_date)

    if YF_data is not None:
        # adding a few columns
        YF_data['Date'] = YF_data.index
        YF_data['Ticker'] = ticker_symbol

        # store data
        store_data_in_mongodb(data=YF_data, collection=collection, collection_ID='Yahoo_Finance')

        print(f"Inserted data for {ticker_symbol}, starting date: {start_date}, ending data: {end_date}\n")
        print(YF_data.describe())
    else:
        print("No data has been added to the database")