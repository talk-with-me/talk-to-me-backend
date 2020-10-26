from flask import Flask, render_template, redirect, url_for, jsonify, request, Response
from flask_socketio import SocketIO, send, join_room, leave_room
from flask_pymongo import PyMongo
#import config
import db, json, datetime, random, uuid
from bson import json_util, ObjectId

# Configure app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'ttm'
mdb = PyMongo(app, db.MONGO_URL).db 

# INSERT ROOM DB

socketio = SocketIO(app, cors_allowed_origins='*')

def json_response(data):
    def callable(response=None, *args, **kwargs):
        return Response(json.dumps(data), *args, **kwargs)
    return callable

# assign users a generated userID and secret. Stores user in db then redirects to queue selection
@app.route('/auth', methods = ['GET'])
def userAuth():
    global userSecret
    userID = "user" + str(random.randint(0, 1000))
    userSecret = str(uuid.uuid4())
    userObj = {"ip": request.remote_addr, "userID": userID, "_id": userSecret, "queueType": "idle", "time": datetime.datetime.utcnow(), "room": "lonely"}
    mdb.userDetails.insert_one(userObj)
    return userObj

# i think this function should be running constantly in the background until there is no one in the queue
# idk how you would make it to constantly run like that...
# currently, doesn't pop users off the queue, so they stay there
@app.route('/isQueueReady', methods=['GET'])
def isQueueReady():
    # count the number of people in the current queryType
    # eventually replace 1 with whichever queryType user needs
    count = mdb.userDetails.count_documents({"queryType": 1})
    if(count >= 2):
        # this should find the first two people in the queue
        query = mdb.userDetails.find(
                {"queryType": 1}, {"ip": 1, "_id": 0}).limit(2)
        output = {}
        ip = [] # store the first two ip here, currently not using it for anything
        i = 0
        for x in query:
            output[i] = x
            ip.append(x['ip'])
            print(ip[i])
            i += 1
        return output # this should be returning the two ip addresses, instead of the dictinoary

    # if there isn't enough people in the 'preferred' queue, then match with someone in another (NOT IMPLEMENTED)
    # if not enough in either, then continue waiting
    else:
        return "Not enough people..."

# When a selection is made, the user's respective fiels are updated in the db
@app.route('/queue', methods = ['POST'])
def requestQueue():
    jsonObj = request.json
    userObject = mdb.userDetails.find_one(jsonObj['userID']) # Fetches user from db
    if (userObject != None): # TODO: return different response if user is already in queue or in a room
        mdb.userDetails.update_one(userObject, {"$set": {"queueType": "inQueue", "time": datetime.datetime.utcnow()}})
        return "STUFF"
    return "ERROR"

# rest api endpoint to assign a room to a user (doesn't join) TODO: make this a scheduled event running on backend
@app.route('/room', methods = ["POST"])
def assign_room():
    jsonObj = request.json
    userObj = mdb.userDetails.find_one(jsonObj['_id']) # get user from db
    mdb.userDetails.update_one(userObj, {"$set": {'room': jsonObj['room'], "queueType": 2, "time": datetime.datetime.utcnow()}})
    return ('room assigned ' + jsonObj['room'])

# sends message to all users connected to same room as sender
@socketio.on('send_message_to_server')
def handleMessage():
    jsonObj = request.json
    userObj = mdb.userDetails.find_one(jsonObj['_id'])
    if(userObj == None):
        return 'Not authorized' # TODO when an unauthorized user tries to send a message
    print('Message: ' + jsonObj['message'])
    # broadcast is set to true so that it's sent to all clients including yourself (so I can see it and the other person can see it)
    socketio.emit('send_message_to_client', jsonObj['message'] ,room = userObj['room'])
    return ('message sent')

# socket event to have user actually join the room
@socketio.on('join_room')
def user_join_room(userId, secret):
    userObj = mdb.userDetails.find_one(userId) # fetch user from db
    if (userObj['secret'] != secret):
        return 'Error: invalid secret'
    join_room(userObj['room'])
    print (userObj['userID'] + ' has joined room ' + userObj['room'])

if __name__ == '__main__':
    socketio.run(app, port=8000, debug=True)
