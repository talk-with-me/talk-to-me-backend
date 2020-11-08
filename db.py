import os

from flask_pymongo import pymongo

# MONGO_URL = "mongodb+srv://twmAdmin:twm999@twmcluster.hgeik.mongodb.net/user?retryWrites=true&w=majority"
# MONGO_URL = "mongodb://localhost:27017/ttm"
MONGO_URL = os.getenv('MONGO_URL')

# client = pymongo.MongoClient(MONGO_URL)
# db = client.get_database('user')
# user_collection = pymongo.collection.Collection(db, 'user_collection')