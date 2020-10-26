from flask import Flask, render_template, redirect, url_for, jsonify, request, Response
from flask_socketio import SocketIO, send, join_room, leave_room
from flask_pymongo import PyMongo
#import config
import db, json, datetime, random
from bson import json_util, ObjectId

# Configure app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'ttm'
mdb = PyMongo(app, db.MONGO_URL).db 

# INSERT ROOM DB

socketio = SocketIO(app, cors_allowed_origins='*')

def jsonResponse(data):
    def callable(response=None, *args, **kwargs):
        return Response(json.dumps(data), *args, **kwargs)
    return callable

# The link that all users will go to first
@app.route('/', methods = ['GET', 'POST'])
def landingPage():
    return redirect(url_for('userAuth'))

# assign users a generated userID and secret. Stores user in db then redirects to queue selection
@app.route('/auth', methods = ['GET'])
def userAuth():
    global userSecret
    userID = "user" + str(random.randint(0, 1000))
    userSecret = random.randint(1000000000, 20000000000)
    user_obj = {"ip": request.remote_addr, "userID": userID, "_id": userSecret, "queueType": 0, "time": datetime.datetime.utcnow(), "room": "lonely"}
    mdb.userDetails.insert_one(user_obj)
    return user_obj

# displays the collection inside the database, so query the db for its values
@app.route('/findAll', methods=['GET'])
def findAll():
    query = mdb.userDetails.find() # 'collection' is the name of the collection in this db
    output = {}
    i = 0
    for x in query:
        output[i] = x
        output[i].pop('_id')
        i += 1

    return output

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

# This would be where the user can choose what type of queue they want to be put in
@app.route('/select', methods = ['POST'])
def selectQueue(): # this is actually the 'landing page' since this is the first page users will actually see
    json_obj = request.json
    if(mdb.userDetails.find_one(json_obj['_id']) != None):
        return render_template('queueSelection.html') # formally was index.html, but different name will help differentiate between chat html and queue page html
    return "ERROR - auth not passed"

# When a selection is made, the user's respective fiels are updated in the db
@app.route('/queue', methods = ['POST'])
def requestQueue():
    json_obj = request.json
    user_object = mdb.userDetails.find_one(json_obj['_id']) # SECRET AUTH
    if (user_object != None):
        print(user_object)
        mdb.userDetails.update_one(user_object, {"$set": {"queueType": 1, "time": datetime.datetime.utcnow()}})
        return render_template('chat.html')
    return "ERROR"

# I personally feel like having this as an event would be better than having it as it's own separate API endpoint
@app.route('/roomID/userID', methods = ['POST'])
def on_join(data):
    user_object = mdb.userDetails.findOne(data['_id']) # SECRET AUTH
    if (user_object != 0):
        room = data['room']
        join_room(room)
        render_template('chat.html', username=userID) # subject to change, userID may be useful for frontend
        send(userID + ' has entered the room.', room=room)

@app.route('/roomID/userID', methods = ['DELETE'])
def on_leave(data):
    user_object = mdb.userDetails.find(data['_id']) # SECRET AUTH
    if (user_object != 0):
        room = data['room']
        leave_room(data['room'], data['username'])
        send(userID + ' has left the room.', room=room)
        mdb.userDetails.delete({"_id": userSecret})

# I believe this should also be handled as an event
@app.route('/messages', methods = ["POST"])
def handleMessage(data):
    json_obj = request.json
    user_obj = mdb.userDetails.find_one(json_obj['_id'])
    if(user_obj == None):
        return 'Not authorized' # TODO when an unauthorized user tries to send a message
    print('Message: ' + data)
    # broadcast is set to true so that it's sent to all clients including yourself (so I can see it and the other person can see it)
    emit(data['message'], room = user_obj['room'])

# rest api endpoint to assign a room to a user (doesn't join)
@app.route('/room', methods = ["POST"])
def assign_room():
    json_obj = request.json
    user_obj = mdb.userDetails.find_one(json_obj['_id']) # get user from db
    mdb.userDetails.update_one(user_obj, {"$set": {'room': json_obj['room'], "queueType": 2, "time": datetime.datetime.utcnow()}})
    return ('room assigned ' + json_obj['room'])

# socket event to have user actually join the room
@socketio.on('join_room')
def user_join_room(json_obj):
    user_obj = mdb.userDetails.find_one(json_obj['_id']) # SECRET AUTH
    print(user_obj['room'])
    join_room(user_obj['room'])
    print (user_obj['userID'] + ' has joined room ' + user_obj['room'])

if __name__ == '__main__':
    socketio.run(app, port=8000, debug=True)
