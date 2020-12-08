# test_main.py - main test file for talk-to-me backend server
import time
import pytest
import requests
import socketio

user = ''

def test_get_auth():
    global user
    r = requests.get('http://localhost:8000/auth')
    user = r.json()['data']
    assert(r.status_code == 200)

def test_bad_enqueue_bad_secret():
    r = requests.post('http://localhost:8000/queue', json={'secret':'fender', 'queueType':'vent'})
    assert(r.status_code == 403)

def test_bad_enqueue_no_queue_type():
    r = requests.post('http://localhost:8000/queue', json={'secret':user['secret']})
    assert(r.status_code == 400)

def test_good_enqueue_vent():
    global user
    r = requests.post('http://localhost:8000/queue', json={'secret':user['secret'], 'queueType':'vent'})
    assert(r.status_code == 200)

def test_two_users_in_vent_get_placed_in_room():
    user1_connected = [False]
    user2_connected = [False]
    user1 = requests.get('http://localhost:8000/auth').json()['data']
    user2 = requests.get('http://localhost:8000/auth').json()['data']

    user1_socket = socketio.Client()
    user2_socket = socketio.Client()
    user1_socket.connect('http://localhost:8000')
    user2_socket.connect('http://localhost:8000')

    @user1_socket.on('queue_complete')
    def on_receive_complete_user1(user):
        print(user, user['user_id'], 'user1: ' + user1['user_id'], user['user_id'] == user1['user_id'])
        if user['user_id'] == user1['user_id']:
            user1_connected[0] = True
            print('user_1 got placed in a room', user1_connected)
            #user1_socket.emit('join_room', user1['secret'])

    @user2_socket.on('queue_complete')
    def on_receive_complete_user1(user):
        if user['user_id'] == user2['user_id']:
            user2_connected[0] = True
            print('user_2 got placed in a room', user2_connected)

    user1_enqueue = requests.post('http://localhost:8000/queue', json={'secret':user1['secret'], 'queueType':'vent'})
    user2_enqueue = requests.post('http://localhost:8000/queue', json={'secret':user2['secret'], 'queueType':'vent'})
    print(user1_enqueue)
    print(user2_enqueue)

    while not user1_connected[0] or not user2_connected[0]:
        print('not connected', user1_connected, user2_connected)
        time.sleep(1)

    user1_socket.disconnect()
    user2_socket.disconnect()
