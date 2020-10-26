from flask import Flask
from flask_pymongo import pymongo


MONGO_URL = "mongodb+srv://twmAdmin:twm999@twmcluster.hgeik.mongodb.net/user?retryWrites=true&w=majority"

client = pymongo.MongoClient(MONGO_URL)
db = client.get_database('user')
user_collection = pymongo.collection.Collection(db, 'user_collection')