

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

        print("\n" +
              "----------------------------------------------------------- \n" +
              "New data inserted: \n" +
              f"- DB: {collection.database.name} \n" +
              f"- Collection: {collection.name} \n" +
              f"- Contract: {list(data.Futures)[0]} \n" +
              "- Expiry: " + list(data.Expiry)[0].strftime("%Y-%m-%d") + "\n" +
              "- From date: " + list(data['Trade Date'])[0].strftime("%Y-%m-%d") + "\n" +
              "- From date: " + list(data['Trade Date'])[-1].strftime("%Y-%m-%d") + "\n" +
              "----------------------------------------------------------- \n"
              )

    except Exception as e:
        print(f"Error storing data " + collection_ID + " in MongoDB: {e}")

