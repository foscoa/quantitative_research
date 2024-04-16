# This is a sample Python script.


import pymongo
import numpy as np
import yfinance as yf

# Create a mongodb client, use default local host
try:
    client = pymongo.MongoClient("mongodb+srv://foscoa:Lsw0r4KyI0rlq8YH@cluster0.vu31vch.mongodb.net/")
except Exception:
    print("Error: " + Exception)

ticker_symbol = "^VIX"  # Example: Apple Inc.
start_date = "2014-01-01"
end_date = "2024-03-31"

def download_YF_data(ticker, start_date, end_date):
    try:
        # Download data
        data = yf.download(ticker, start=start_date, end=end_date)
        return data
    except Exception as e:
        print(f"Error downloading data for {ticker}: {e}")
        return None

YF_data = download_YF_data(ticker_symbol, start_date, end_date)
if YF_data is not None:
    print(YF_data.head())  # Print the first few rows of the downloaded data

YF_data['Date'] = YF_data.index

YF_data['Ticker'] = ticker_symbol


# Function to store data in MongoDB
def store_data_in_mongodb(data, client):
    try:
        db = client['ETFs']
        collection = db['Yahoo_Finance']
        # Insert data into MongoDB
        collection.insert_many(data.to_dict(orient='records'))
        print("Data stored successfully in MongoDB.")
    except Exception as e:
        print(f"Error storing data in MongoDB: {e}")

store_data_in_mongodb(YF_data, client = client)