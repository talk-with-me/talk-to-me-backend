from flask import Flask, render_template, jsonify, request
from flask_pymongo import PyMongo
import db
import datetime
from flask_socketio import SocketIO, send
import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ttm'
mdb = PyMongo(app, db.MONGO_URL).db 

socketio = SocketIO(app, cors_allowed_origins='*')

@app.route('/')
def landingPage():
    return 'Welcome to Talk to Me'

# Preferably there will be a separate app route for the landing page, and then a button the redirects to this app route
@app.route('/room/RANDOM')
def connectToRoom():    
    return render_template('index.html')

@socketio.on('message')
def handleMessage(m):
    print('Message: ' + m)
    # broadcast is set to true so that it's sent to all clients including yourself (so I can see it and the other person can see it)
    send(m, broadcast=True)

# input user data the moment they join into the website
@app.route('/inputData')
def inputData():
    mdb.userDetails.insert_one({"ip": request.remote_addr, "clientID": "some clientID", "secret": 123,  
                                "queryType": 0, "time": datetime.datetime.utcnow()})
    return "Inserted into user collection!"

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

    print(output)
    return output

# finds a specfic row using their secret
# find_one() - if query matches, first document is returned, otherwise null.
# find() - nomatter number of documents matched, a cursor is returned, never null.
# FYI: there is also a find_one_and_update function if needed.
@app.route('/find/<int:secret>', methods=['GET'])
def find(secret):
    query = mdb.userDetails.find_one({"secret": secret}, {"_id": 0}) # ignore _id since its ObjectID, won't display otherwise
    return query

# currently, doesn't pop users off the queue, so they stay there
@app.route('/isQueueReady', methods=['GET'])
def isQueueReady():
    # count the number of people in the current queryType
    # eventually replace 1 with whichever queryType user needs
    count = mdb.userDetails.count_documents({"queueType": "idle"})
    if(count >= 2):
        # this should find the first two people in the queue
        query = mdb.userDetails.find(
                {"queueType": "idle"}, {"ip": 1, "secret": 1, "_id": 0}).limit(2)
        output = {}
        i = 0
        for x in query:
            output[i] = x
            i += 1

        print(output)
        return output

    # if there isn't enough people in the 'preferred' queue, then match with someone in another (NOT IMPLEMENTED)
    # if not enough in either, then continue waiting
    else:
        print("no one")
        return "Not enough people..."

# create schedule for printing time
scheduler = BackgroundScheduler()
scheduler.start()
scheduler.add_job(
    func=isQueueReady,
    trigger=IntervalTrigger(seconds=2),
    id='printing_all',
    name='Print all every 2 seconds',
    replace_existing=True)
# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())


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
    #SocketIO takes the Flask app and wraps the SocketIO functionality around it
    #Typically a Flask app is used in a typical request-response model -  
    #the server will wait for a request to come in, process it, then send a response back
    #
    #SocketIO is more real-time, so the extra functionality is built around this standard Flask app functionality
    #In other words, SocketIO is a specialized add-on to the Flask app functionality for real-time functionality
    socketio.run(app, port=8000)

