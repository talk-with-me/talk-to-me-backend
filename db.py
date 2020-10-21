from flask import Flask
from flask_pymongo import pymongo
from app import app

# this is how it connects to MongoDB Atlas
# Username: twmAdmin
# password: talk123
# Cluster Name: twmcluster
CONNECTION_STRING = "mongodb+srv://twmAdmin:talk123@twmcluster.hgeik.mongodb.net/<database>?retryWrites=true&w=majority"

client = pymongo.MongoClient(CONNECTION_STRING)
db = client.get_database('flask_mongodb_atlas')
user_collection = pymongo.collection.Collection(db, 'user_collection')