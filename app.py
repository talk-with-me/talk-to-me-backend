from flask import Flask, render_template
from flask_socketio import SocketIO, send, join_room, leave_room
from models import *
from flask_login import LoginManager, login_user, current_user

# Configure app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'ttm'
socketio = SocketIO(app, cors_allowed_origins='*')

#Configure database
# Will probably be just merging in Alex's code in here since db on his branch is set up

login = LoginManager(app)
login.init_app(app)

@login.user_loader
def load_user(secret):
    return #User object from finding secret in db

@app.route('/', methods = ['GET', 'POST'])
def landingPage():
    return redirect(url_for('auth'))

@app.route('/auth', methods = ['POST'])
def userAuth():
    userID = 'SOME RANDOM ID' # random ID assigned automatically
    userSecret = 'SOME RANDOM SECRET'
    user_object = User(ip = "SOME IP", id = userID, secret = userSecret, inQueue = False, queueType = "NONE", enteredQueueAt = "NONE")
    db.add(user_object)
    load_user(user_object.secret)
    return redirect(url_for('select'))

@app.route('/select', methods = ['POST'])
def queueSelectPage(): # this is actually the landing page
    return render_template('queueSelection.html') # formally was index.html, but different name will help differentiate between chat html and landing page html

@app.route('/queue', methods['POST'])
def requestQueue(id, secret):
    user_object = # find user via id
    if (user_object.secret == secret) {
        user_object.inQueue = True
        user_object.queueType = "Talk To Me"
        user_object.enteredQueueAt = sometimestamp
    }

@app.route('/roomID/userID', methods['POST'])
def on_join(data):
    if(current_user.secret = data['secret'])
        userID = data["userID"]
        room = data["room"]
        render_template('chat.html', current_user.id) # subject to change, current_user.id may be useful for frontend
        join_room(room)
        send(userID + ' has entered the room.', room=room)
    # this is why login is useful - we 'automatically login' users, giving them a session and a given, anonymized username

@app.route('/roomID/userID', methods['DELETE'])
def on_leave(data):
    if(current_user.secret == data['secret'])
        userID = data['userID']
        room = data['room']
        leave_room(data['room'], data['username'])
        send(userID + ' has left the room.', room=room)

@socketio.on('message') # this should be handled as an event - not an endpoint
def handleMessage(data):
    print('Message: ' + data)
    # broadcast is set to true so that it's sent to all clients including yourself (so I can see it and the other person can see it)
    send(data['message'], broadcast=True, room = data['room'])


if __name__ == '__main__':
    #SocketIO takes the Flask app and wraps the SocketIO functionality around it
    #Typically a Flask app is used in a typical request-response model -  
    #the server will wait for a request to come in, process it, then send a response back
    #
    #SocketIO is more real-time, so the extra functionality is built around this standard Flask app functionality
    #In other words, SocketIO is a specialized add-on to the Flask app functionality for real-time functionality
    socketio.run(app, port=8000)