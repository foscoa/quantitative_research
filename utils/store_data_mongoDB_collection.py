

# Function to store data in MongoDB collection
def store_data_in_mongodb(data, collection, collection_ID):
    try:

        # Insert data into MongoDB
        collection.insert_many(data.to_dict(orient='records'))
        print("Data " + collection_ID + " stored successfully in MongoDB.")
    except Exception as e:
        print(f"Error storing data " + collection_ID + " in MongoDB: {e}")

