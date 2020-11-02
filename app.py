from flask import Flask, render_template, redirect, url_for, jsonify, request, Response
from flask_cors import CORS
from flask_socketio import SocketIO, send, join_room, leave_room
from flask_pymongo import PyMongo
#import config
import db, json, datetime, random, uuid
from bson import json_util, ObjectId
from lib import errors

# Configure app
from lib.utils import clean_json, error, expect_json, success

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ttm'
CORS(app)
mdb = PyMongo(app, db.MONGO_URL).db
socketio = SocketIO(app, cors_allowed_origins='*')

# ===== REST =====
# assign users a generated userID and secret. Stores user in db then redirects to queue selection
@app.route('/auth', methods = ['GET'])
def userAuth():
    userID = str(uuid.uuid4())
    userSecret = str(uuid.uuid4())
    userObj = {
        "ip": request.remote_addr, "userID": userID, "secret": userSecret, "queueType": "idle",
        "time": datetime.datetime.utcnow(), "room": "lonely", "sid": None
    }
    mdb.userDetails.insert_one(userObj)
    return success(userObj)

# When a selection is made, the user's respective fiels are updated in the db
@app.route('/queue', methods = ['POST'])
@expect_json(secret=str)
def requestQueue(body):
    userObject = mdb.userDetails.find_one({"secret": body['secret']}) # Fetches user from db
    if (userObject != None): # TODO: return different response if user is already in queue or in a room
        mdb.userDetails.update_one({"secret": body['secret']},
                                   {"$set": {"queueType": "inQueue", "time": datetime.datetime.utcnow()}})
        return success("yay, you are in queue now", 200)
    return error(403, "go do auth first you dummy")

# sends message to all users connected to same room as sender
@app.route('/messages', methods = ['POST'])
@expect_json(secret=str, message=str, nonce=str)
def handleMessage(jsonObj):
    userObj = mdb.userDetails.find_one({"secret": jsonObj['secret']})
    if(userObj == None):
        return error(403, "do auth first you dummy")
    room_id = userObj['room']
    user_id = userObj['userID']
    print('Message: ' + jsonObj['message'])
    message = {
        # _id autogenerated
        "room_id": room_id,
        "author": user_id,
        "timestamp": datetime.datetime.now(),
        "nonce": jsonObj['nonce'],
        "content": jsonObj['message']
    }
    mdb.messages.insert_one(message)
    socketio.emit('send_message_to_client', clean_json(message) ,room = room_id)
    return success(message, 201)

def delete_user_from_db(userObj):
    mdb.userDetails.delete_one({'secret': userObj['secret']})
    mdb.messages.delete_many({'author': userObj['userID']}) # can proablby do by roomID
    mdb.rooms.delete_one({'room': userObj['room']})

# ====== SOCKET STUFF =====
# socket event to have user actually join the room
@socketio.on('join_room')
def user_join_room(secret):
    userObj = mdb.userDetails.find_one({'secret': secret}) # fetch user from db
    if userObj is None:
        print("bad user not found")
        return
    join_room(userObj['room'])
    socketio.emit('user_connected', room=userObj['room'])
    print (userObj['userID'] + ' has joined room ' + userObj['room'])

# user has left your channel
@socketio.on('leave_room')
def user_leave_room(secret):
    userObj = mdb.userDetails.find_one({'secret': secret})  # fetch user from db
    if userObj is None:
        print("bad user not found")
        return
    # todo whatever teardown you need
    socketio.emit('user_disconnected', room=userObj['room'])
    # delete these 2 users from messages, rooms, and queue
    delete_user_from_db(userObj)
    print(userObj['userID'] + ' has left room ' + userObj['room'])

@socketio.on('hello')
def user_sid_assoc(secret):
    """
    Associates a SocketIO session ID with a user object. This is called immediately after the user auths.
    """
    user = mdb.userDetails.find_one({'secret': secret})  # fetch user from db
    if user is None:
        print("user_sid_assoc: user not found")
        return
    # noinspection PyUnresolvedReferences
    # provided by socketio
    sid = request.sid
    mdb.userDetails.update_one({'secret': secret}, {"$set": {"sid": sid}})
    print(f"User {user['userID']} has socket session ID {sid}")

@socketio.on('disconnect')
def user_disconnect():
    # this code was copied from leave_room - modify as needed
    # noinspection PyUnresolvedReferences
    userObj = mdb.userDetails.find_one({'sid': request.sid})  # fetch user from db
    if userObj is None:
        print("user disconnected from socket but we don't know them")
        return
    socketio.emit('user_disconnected', room=userObj['room'])
    # delete these 2 users from messages, rooms, and queue
    delete_user_from_db(userObj)
    print(userObj['userID'] + ' has left room ' + userObj['room'])

# ===== MISC =====
# register handlers and stuff
errors.register_error_handlers(app)

# ===== DEV ONLY ====
# currently, doesn't pop users off the queue, so they stay there

def notify_queue_complete(user_id):
    socketio.emit("queue_complete", {'user_id' : user_id[0]})
    socketio.emit("queue_complete", {'user_id' : user_id[1]})

def match_making(userIDs):
    roomID = str(uuid.uuid4())
    user_ID1 = userIDs[0]
    user_ID2 = userIDs[1]
    mdb.rooms.insert_one({"room" : roomID, 'user1' : user_ID1, 'user2' : user_ID2})
    print("user " + user_ID1 + " and user " + user_ID2 + " have been assigned room " + roomID + " and have been removed from the db")

@app.route('/isQueueReady', methods=['GET'])
#@app.before_first_request
def isQueueReady():
    # count the number of people in the current queueType inQueue
    # eventually replace 1 with whichever queueType user needs
    count = mdb.userDetails.count_documents({"queueType": "inQueue"})
    if(count >= 2):
        # this should find the first two people in the queue
        query = mdb.userDetails.find(
                {"queueType": "inQueue"}, {"userID": 1, "secret": 1, "_id": 0}).limit(2)
        output = {}
        userIDs = []
        i = 0
        for x in query:
            output[i] = x
            userIDs.append(x['userID'])
        match_making(userIDs)
        notify_queue_complete(userIDs) # pass user_id into notify_queue_complete()
        mdb.userDetails.delete_one({"userID" : userIDs[0]})
        mdb.userDetails.delete_one({"userID" : userIDs[1]})
        return output

    # if there isn't enough people in the 'preferred' queue, then match with someone in another (NOT IMPLEMENTED)
    # if not enough in either, then continue waiting
    else:
        return "no one"

# ---------------------MAKE SURE TO REMOVE THESE ON RELEASE-----------------------------
# deletes all documents in UserDetails
@app.route('/deleteUserDetails')
def delete_user_details():
    mdb.userDetails.delete_many({})
    return "deleted all docs in userDetails"

@app.route('/deleteRoomDetails')
def delete_room_details():
    mdb.rooms.delete_many({})
    return "deleted all docs in rooms"

@app.route('/deleteMessageDetails')
def delete_message_details():
    mdb.messages.delete_many({})
    return "deleted all docs in messages"

@app.route('/deleteAllDetails')
def delete_all_details():
    mdb.userDetails.delete_many({})
    mdb.rooms.delete_many({})
    mdb.messages.delete_many({})
    return "all gone!"

# APScheduler running in background
scheduler = BackgroundScheduler()
scheduler.start()
scheduler.add_job(
    func=isQueueReady,
    trigger=IntervalTrigger(seconds=4),
    id='check_is_queue_ready',
    name='Check queue status every 4 seconds',
    replace_existing=True)
# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())


if __name__ == '__main__':
    socketio.run(app, port=8000, debug=True)
