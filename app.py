from flask import Flask, render_template, redirect, url_for, jsonify, request, Response
from flask_socketio import SocketIO, send, join_room, leave_room
from flask_pymongo import PyMongo
#import config
import db, json, datetime, random, uuid
from bson import json_util, ObjectId
from lib import errors

# Configure app
from lib.utils import error, expect_json, success

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ttm'
mdb = PyMongo(app, db.MONGO_URL).db

# INSERT ROOM DB

socketio = SocketIO(app, cors_allowed_origins='*')

# ===== REST =====
# assign users a generated userID and secret. Stores user in db then redirects to queue selection
@app.route('/auth', methods = ['GET'])
def userAuth():
    userID = str(uuid.uuid4())
    userSecret = str(uuid.uuid4())
    userObj = {"ip": request.remote_addr, "userID": userID, "secret": userSecret, "queueType": "idle", "time": datetime.datetime.utcnow(), "room": "lonely"}
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
    socketio.emit('send_message_to_client', message ,room = room_id)
    return success(message, 201)

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
    print(userObj['userID'] + ' has left room ' + userObj['room'])

@socketio.on('disconnect')
def user_disconnect():
    # todo
    pass

# ===== MISC =====
def notify_queue_complete():
    socketio.emit("queue_complete", {'user_id': 'blah'})


# register handlers and stuff
errors.register_error_handlers(app)

# ===== DEV ONLY ====
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

# rest api endpoint to assign a room to a user (doesn't join) TODO: make this a scheduled event running on backend
@app.route('/room', methods = ["POST"])
def assign_room():
    jsonObj = request.json
    userObj = mdb.userDetails.find_one(jsonObj['_id']) # get user from db
    mdb.userDetails.update_one(userObj, {"$set": {'room': jsonObj['room'], "queueType": 2, "time": datetime.datetime.utcnow()}})
    return ('room assigned ' + jsonObj['room'])


# APScheduler running in background 
scheduler = BackgroundScheduler()
scheduler.start()
scheduler.add_job(
    func=isQueueReady,
    trigger=IntervalTrigger(seconds=2),
    id='check_is_queue_ready',
    name='Check queue statsu every 2 seconds',
    replace_existing=True)
# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())


if __name__ == '__main__':
    socketio.run(app, port=8000, debug=True)
