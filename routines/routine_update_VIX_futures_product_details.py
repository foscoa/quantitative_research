'''
This script scrapes product details for VIX future contracts from the CBOE website using BeautifulSoup. It retrieves the
 relevant data, checks if the product already exists in MongoDB (DB: Listed_Futures, COLL: Product_List), and then saves
  the details if it's a new entry.
'''

import requests
from bs4 import BeautifulSoup
import re
import pymongo
import json
import time
from datetime import datetime

### GET NEW DATA FROM CBOE WEBSITE -------------------------------------------------------------------------------------

# URL of the website
url = "https://www.cboe.com/us/futures/market_statistics/historical_data/"

# Send a GET request to fetch the HTML content
response = requests.get(url)
response.raise_for_status()  # Check if the request was successful

# Parse the HTML content using BeautifulSoup
soup = BeautifulSoup(response.text, 'html.parser')

# Search for the script tag that contains the JS variable
script_tag = soup.find('script', string=re.compile("CTX.defaultProductList")).string.split(";")[1].split("=")[1]

# Convert the string to a dictionary
data = json.loads(script_tag)

### UPDATE DATABASE ----------------------------------------------------------------------------------------------------

# Create mongodb client
client = pymongo.MongoClient("mongodb+srv://foscoa:Lsw0r4KyI0rlq8YH@cluster0.vu31vch.mongodb.net/")
db = client['Listed_Futures']
collection = db['Product_List']

# print last modification time
def print_last_modification_time(collection):

    # Print when database was last modified
    last_document = collection.find_one(sort=[('_id', -1)])

    if last_document:
        # Extract timestamp from ObjectId
        last_modified_time = last_document['_id'].generation_time
        print(f"Last modification time: {last_modified_time}")
    else:
        print("Collection is empty.")
print_last_modification_time(collection=collection)

# Find latest expire date and initialize it as a cutoff date
cutoff_date = collection.find_one({}, sort=[("expire_date", -1)])['expire_date']

# Find all sub-dictionaries where expire_date > cutoff_date
result = {}
for year, contracts in data.items():
    list_of_contracts = []
    for contract in contracts:
        expire_date = datetime.strptime(contract['expire_date'], "%Y-%m-%d")
        if expire_date > datetime.strptime(cutoff_date, '%Y-%m-%d'):
            list_of_contracts.append(contract)
    result[year] = list_of_contracts

# Remove empty lists from the dictionary
cleaned_result = {key: value for key, value in result.items() if value}

count_new_inserts = 0
for year in cleaned_result.keys():
    for curr_data in cleaned_result[year]:

        current_product = curr_data['product_display']

        # Define the query to check if the product exists
        query = {"product_display": current_product}

        if not collection.find_one(query):

            # Remove unnecessary fields and adding timestamp
            curr_data.pop('contract_dt')
            curr_data.pop('futures_root')
            curr_data.pop('product_display')
            curr_data['Timestamp'] = time.ctime()

            # Define the new product data to insert if it doesn't exist
            new_product = {"$setOnInsert": curr_data}

            # Perform the upsert operation
            result = collection.update_one(query, new_product, upsert=True)

            # Check if a document was inserted
            if result.matched_count == 0:
                print(f"Product {current_product} with maturity {curr_data['expire_date']} was inserted.")
                count_new_inserts +=1

if count_new_inserts > 0:
    print("Total number of added products: " + str(count_new_inserts))
else:
    print("No new product has been found")


