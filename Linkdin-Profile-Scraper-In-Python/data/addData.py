# import json
# from pymongo import MongoClient

# # MongoDB connection details
# MONGO_URI = "mongodb://localhost:27017/" # Adjust if your MongoDB is on a different host/port
# DATABASE_NAME = "Linkedin"
# COLLECTION_NAME = "profile_data"
# JSON_FILE_PATH = "data\data.json" # Path to your JSON file

# try:
#     # Connect to MongoDB
#     client = MongoClient(MONGO_URI)
#     db = client[DATABASE_NAME]
#     collection = db[COLLECTION_NAME]

#     # Load JSON data from file
#     with open(JSON_FILE_PATH, 'r') as file:
#         file_data = json.load(file)

#     # Insert data into the collection
#     if isinstance(file_data, list):
#         collection.insert_many(file_data)
#         print(f"Successfully inserted {len(file_data)} documents into '{COLLECTION_NAME}'.")
#     else:
#         collection.insert_one(file_data)
#         print(f"Successfully inserted 1 document into '{COLLECTION_NAME}'.")

# except Exception as e:
#     print(f"An error occurred: {e}")

# finally:
#     # Close the MongoDB connection
#     if 'client' in locals() and client:
#         client.close()


import json
from pymongo import MongoClient

# MongoDB connection details
MONGO_URI = "mongodb://localhost:27017/"  # Adjust if your MongoDB is on a different host/port
DATABASE_NAME = "Linkedin"
COLLECTION_NAME = "profile_data"

# Corrected path to the JSON file using forward slashes for cross-platform compatibility
JSON_FILE_PATH = "D:\Linkdin-Profile-Scraper-In-Python\Mukund_Savaliya_profile_data.json"

try:
    # Connect to MongoDB
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    collection = db[COLLECTION_NAME]

    # Drop the unique index on the 'url' field to allow for documents without a 'url'
    try:
        collection.drop_index("url_1")
        print("Dropped the unique index 'url_1' to avoid duplicate key errors.")
    except Exception as e:
        print(f"Index 'url_1' not found or could not be dropped: {e}")

    # Load JSON data from file
    with open(JSON_FILE_PATH, 'r') as file:
        file_data = json.load(file)

    # Insert data into the collection
    if isinstance(file_data, list):
        collection.insert_many(file_data)
        print(f"Successfully inserted {len(file_data)} documents into '{COLLECTION_NAME}'.")
    else:
        collection.insert_one(file_data)
        print(f"Successfully inserted 1 document into '{COLLECTION_NAME}'.")

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    # Close the MongoDB connection
    if 'client' in locals() and client:
        client.close()