# test_main.py - main test file for talk-to-me backend server
import time
import pytest
import requests
import socketio

# wait for server to start up
requests.get('http://localhost:8000')

user1_connected = [False]
user2_connected = [False]
user3_connected = [False]
user4_connected = [False]

user1_received_messages = []
user2_received_messages = []
user3_received_messages = []
user4_received_messages = []

user1_socket = socketio.Client()
user2_socket = socketio.Client()
user3_socket = socketio.Client()
user4_socket = socketio.Client()
user1_socket.connect('http://localhost:8000')
user2_socket.connect('http://localhost:8000')
user3_socket.connect('http://localhost:8000')
user4_socket.connect('http://localhost:8000')

@user1_socket.on('queue_complete')
def on_receive_complete_user1(user):
    user1_socket.emit('join_room', user1['secret'])
    print(user, user['user_id'], 'user1: ' + user1['user_id'], user['user_id'] == user1['user_id'])
    if user['user_id'] == user1['user_id']:
        user1_connected[0] = True
        print('user_1 got placed in a room', user1_connected)
        #user1_socket.emit('join_room', user1['secret'])

@user2_socket.on('queue_complete')
def on_receive_complete_user2(user):
    user2_socket.emit('join_room', user2['secret'])
    print(user, user['user_id'], 'user2: ' + user2['user_id'], user['user_id'] == user2['user_id'])
    if user['user_id'] == user2['user_id']:
        user2_connected[0] = True
        print('user_2 got placed in a room', user2_connected)

@user3_socket.on('queue_complete')
def on_receive_complete_user3(user):
    user3_socket.emit('join_room', user3['secret'])
    print(user, user['user_id'], 'user3: ' + user3['user_id'], user['user_id'] == user3['user_id'])
    if user['user_id'] == user3['user_id']:
        user3_connected[0] = True
        print('user_3 got placed in a rjom', user3_connected)

@user4_socket.on('queue_complete')
def on_receive_complete_user4(user):
    user4_socket.emit('join_room', user4['secret'])
    print(user, user['user_id'], 'user4: ' + user4['user_id'], user['user_id'] == user4['user_id'])
    if user['user_id'] == user4['user_id']:
        user4_connected[0] = True
        print('user_4 got placed in a room', user4_connected)

@user1_socket.on('send_message_to_client')
def on_receive_complete_user1(message):
    user1_received_messages.append(message)
    print('user1 received message:', message)

@user2_socket.on('send_message_to_client')
def on_receive_complete_user2(message):
    user2_received_messages.append(message)
    print('user2 received message:', message, len(user2_received_messages))

@user3_socket.on('send_message_to_client')
def on_receive_complete_user3(message):
    user3_received_messages.append(message)
    print('user3 received message:', message)

@user4_socket.on('send_message_to_client')
def on_receive_complete_user4(message):
    user4_received_messages.append(message)
    print('user4 received message:', message)

user1 = ''
user2 = ''
user3 = ''
user4 = ''

def test_get_auth():
    print('testing get auth')
    global user1
    global user2
    global user3
    global user4
    user1 = requests.get('http://localhost:8000/auth').json()['data']
    user2 = requests.get('http://localhost:8000/auth').json()['data']
    user3 = requests.get('http://localhost:8000/auth').json()['data']
    user4 = requests.get('http://localhost:8000/auth').json()['data']

def test_bad_auth():
    print('testing get auth')
    r = requests.post('http://localhost:8000/auth')
    assert(r.status_code == 405)

def test_bad_enqueue_bad_secret():
    print('testing enqueue bad secret')
    r = requests.post('http://localhost:8000/queue', json={'secret':'fender', 'queueType':'vent'})
    assert(r.status_code == 403)

def test_bad_enqueue_no_queue_type():
    print('testing enqueue bad enqueue type')
    r = requests.post('http://localhost:8000/queue', json={'secret':user1['secret']})
    assert(r.status_code == 400)

def test_bad_enqueue_get():
    print('testing enqueue bad enqueue type')
    r = requests.get('http://localhost:8000/queue')
    assert(r.status_code == 405)

def test_good_enqueue_vent():
    print('testing good vent enqueue')
    global user1
    r = requests.post('http://localhost:8000/queue', json={'secret':user1['secret'], 'queueType':'vent'})
    assert(r.status_code == 200)

def test_good_enqueue_listen():
    print('testing good listen enqueue')
    global user2
    r = requests.post('http://localhost:8000/queue', json={'secret':user2['secret'], 'queueType':'listen'})
    assert(r.status_code == 200)

def test_good_enqueue_talk():
    print('testing good talk enqueue')
    global user3
    global user4
    r1 = requests.post('http://localhost:8000/queue', json={'secret':user3['secret'], 'queueType':'talk'})
    r2 = requests.post('http://localhost:8000/queue', json={'secret':user4['secret'], 'queueType':'talk'})
    assert(r1.status_code == 200)
    assert(r2.status_code == 200)

def test_two_users_in_talk_and_vent_get_placed_in_room():
    print('testing talk and vent matchmaking')

    while not user3_connected[0] or not user4_connected[0]:
        print('not connected', user3_connected, user4_connected)
        time.sleep(1)

    user3_socket.disconnect()
    user4_socket.disconnect()

def test_two_users_in_listen_get_placed_in_room():
    print('testing listen matchmaking')

    while not user1_connected[0] or not user2_connected[0]:
        print('not connected', user1_connected, user2_connected)
        time.sleep(1)

def test_sending_messages():
    print('testing sending messages')
    r1 = requests.post('http://localhost:8000/messages', json={'secret':user1['secret'], 'message':'hello1', 'nonce':'nunce'})
    print(r1.json())
    assert(r1.status_code == 201)

def test_receiving_messages():
    print('testing receiving messages')
    global user2_received_message
    while len(user2_received_messages) < 1:
        print('user2 not received message')
        time.sleep(1)

    user1_socket.disconnect()
    user2_socket.disconnect()
