# This is a sample Python script.

import pymongo
import pandas as pd
from datetime import datetime
from utils.store_data_mongoDB_collection import *

def read_csv_from_url(url):
    try:
        # Read the CSV file from the URL
        df = pd.read_csv(url)
        return df
    except Exception as e:
        print("Error:", e)
        return None


# Create a mongodb client, use default local host
try:
    client = pymongo.MongoClient("mongodb+srv://foscoa:Lsw0r4KyI0rlq8YH@cluster0.vu31vch.mongodb.net/")
except Exception:
    print("Error: " + Exception)

db = client['Listed_Futures']
collection = db['Product_List']

# Specify the field for which you want to find distinct values
field = "duration_type"

# Find distinct values for the specified field
distinct_values = collection.distinct(field)

# Print the distinct values
print("Distinct values for", field, ":", distinct_values)

# Query:
query = {"duration_type": "M"}

# Projection:
projection = {"_id": 0, "path": 1}

# Perform the query with projection
result = collection.find(query, projection)

# Iterate over the result and print each document
paths = [document['path'] for document in result]

##

for path in paths:
    url = "https://cdn.cboe.com/" + path

    # Read data from CBOE website
    data_frame = read_csv_from_url(url)
    expiry_string = url[-14:-4]
    data_frame['Expiry'] = expiry_string # create column with expiration date
    data_frame.drop('EFP', inplace= True, axis = 1)

    db = client['Listed_Futures']
    collection = db['CBOE_VIX_Futures_monthly']

    store_data_in_mongodb(data=data_frame,
                          collection=collection,
                          collection_ID=expiry_string)


