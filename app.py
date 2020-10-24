from flask import Flask, render_template, jsonify, request
from flask_pymongo import PyMongo
#import config
import db
import datetime
from flask_socketio import SocketIO, send

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
    mdb.userDetails.insert_one({"ip": request.remote_addr, "clientID": "some clientID", "secret": "some secret",  
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



if __name__ == '__main__':
    #SocketIO takes the Flask app and wraps the SocketIO functionality around it
    #Typically a Flask app is used in a typical request-response model -  
    #the server will wait for a request to come in, process it, then send a response back
    #
    #SocketIO is more real-time, so the extra functionality is built around this standard Flask app functionality
    #In other words, SocketIO is a specialized add-on to the Flask app functionality for real-time functionality
    socketio.run(app, port=8000)