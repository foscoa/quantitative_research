'''
This script downloads futures data from the CBOE website, with root "https://cdn.cboe.com/" and
uploads the results on mongoDB. The url paths are saved in Listed_Futures (DB)/Product_List (COL).
The result is saved in Listed_Futures (DB)/CBOE_VIX_Futures_monthly (COL)
'''

import pymongo
import pandas as pd
from utils.store_data_mongoDB_collection import *
from datetime import datetime

# Create mongodb client
client = pymongo.MongoClient("mongodb+srv://foscoa:Lsw0r4KyI0rlq8YH@cluster0.vu31vch.mongodb.net/")

def read_csv_from_url(url):
    try:
        # Read the CSV file from the URL
        df = pd.read_csv(url)
        return df
    except Exception as e:
        print("Error:", e)
        return None

# database features
db_Listed_Futures = client['Listed_Futures']
collection_Product_List = db_Listed_Futures['Product_List']

# Specify the field for which you want to find distinct values
field = "duration_type"
distinct_values = collection_Product_List.distinct(field)
# print("Distinct values for", field, ":", distinct_values)

# Find paths for duration type M:
query = {"duration_type": "M"}
projection = {"_id": 0, "path": 1}
result = collection_Product_List.find(query, projection)

# Iterate over the result and print each document
paths = [document['path'] for document in result]

##

db = client['Listed_Futures']
collection = db['CBOE_VIX_Futures_monthly']

count_new_inserts = 0
for path in paths:

    url = "https://cdn.cboe.com/" + path
    expiry_datetime = pd.to_datetime(url[-14:-4])

    # Find contracts to update: those who have an expiry which is later than the last date in the db
    # [datetime.strptime(exp[-14:-4], "%Y-%m-%d") for exp in paths]

    # Define the query to check if the future exists
    query = {"Expiry": expiry_datetime}
    projection = {'_id':0, 'Trade Date':1}
    last_date_dictionary = collection.find_one(query, projection, sort=[('Trade Date', -1)])

    if last_date_dictionary is None:
        # Initialize a very old datetime (January 1, 1000)
        last_date = datetime(2000, 1, 1)
    else:
        last_date = last_date_dictionary['Trade Date']

    if last_date < expiry_datetime:

        # Read data from CBOE website
        data_frame = read_csv_from_url(url)

        if last_date < datetime.strptime(list(data_frame['Trade Date'])[-1], '%Y-%m-%d'):
            data_frame['Expiry'] = expiry_datetime  # create column with expiration date
            data_frame.drop('EFP', inplace=True, axis=1)
            data_frame['Trade Date'] = pd.to_datetime(data_frame['Trade Date'])
            data_frame = data_frame[data_frame['Trade Date'] > last_date]

            store_data_in_mongodb(data=data_frame,
                                  collection=collection,
                                  collection_ID=str(expiry_datetime))
            count_new_inserts += 1



if count_new_inserts > 0:
    print(f"The number of contracts modified or added is: {count_new_inserts}")
else:
    print("No contract has been modified or added")


