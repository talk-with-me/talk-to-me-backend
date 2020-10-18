from flask import Flask, render_template
from flask_socketio import SocketIO, send

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ttm'
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

if __name__ == '__main__':
    #SocketIO takes the Flask app and wraps the SocketIO functionality around it
    #Typically a Flask app is used in a typical request-response model -  
    #the server will wait for a request to come in, process it, then send a response back
    #
    #SocketIO is more real-time, so the extra functionality is built around this standard Flask app functionality
    #In other words, SocketIO is a specialized add-on to the Flask app functionality for real-time functionality
    socketio.run(app, port=8000)