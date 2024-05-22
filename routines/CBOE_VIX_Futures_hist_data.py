'''
This script download futures data from the CBOE website, with root "https://cdn.cboe.com/" and
uploads the results on mongoDB. The url pathes are saved in Listed_Futures (DB)/Product_List (COL).
The result is saved in Listed_Futures (DB)/CBOE_VIX_Futures_monthly (COL)
'''

import pymongo
import pandas as pd
from utils.store_data_mongoDB_collection import *

def read_csv_from_url(url):
    try:
        # Read the CSV file from the URL
        df = pd.read_csv(url)
        return df
    except Exception as e:
        print("Error:", e)
        return None


# Create mongodb client
client = pymongo.MongoClient("mongodb+srv://foscoa:Lsw0r4KyI0rlq8YH@cluster0.vu31vch.mongodb.net/")
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

db = client['Listed_Futures']
collection = db['CBOE_VIX_Futures_monthly']

for path in paths:
    url = "https://cdn.cboe.com/" + path

    # Read data from CBOE website
    data_frame = read_csv_from_url(url)
    expiry_string = url[-14:-4]
    data_frame['Expiry'] = pd.to_datetime(expiry_string)    # create column with expiration date
    data_frame.drop('EFP', inplace=True, axis=1)
    data_frame['Trade Date'] = pd.to_datetime(data_frame['Trade Date'])

    store_data_in_mongodb(data=data_frame,
                          collection=collection,
                          collection_ID=expiry_string)


