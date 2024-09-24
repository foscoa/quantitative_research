

# Function to store data in MongoDB collection
def store_data_in_mongodb(data, collection, collection_ID):
    '''
    :param data: data to store
    :param collection: MongoDB collection
    :param collection_ID: for printing purposes only
    :return: nothing
    '''
    try:
        # Insert data into MongoDB
        collection.insert_many(data.to_dict(orient='records'))
        print("Data " + collection_ID + " stored successfully in MongoDB.")
    except Exception as e:
        print(f"Error storing data " + collection_ID + " in MongoDB: {e}")

