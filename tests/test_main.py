# test_main.py - main test file for talk-to-me backend server
import time
import pytest
import requests
import socketio

user = ''

def test_get_auth():
    print('testing get auth')
    global user
    r = requests.get('http://localhost:8000/auth')
    user = r.json()['data']
    assert(r.status_code == 200)

def test_bad_enqueue_bad_secret():
    print('testing enqueue bad secret')
    global user
    r = requests.post('http://localhost:8000/queue', json={'secret':'fender', 'queueType':'vent'})
    assert(r.status_code == 403)

def test_bad_enqueue_no_queue_type():
    print('testing enqueue bad enqueue type')
    r = requests.post('http://localhost:8000/queue', json={'secret':user['secret']})
    assert(r.status_code == 400)

def test_good_enqueue_vent():
    print('testing good enqueue')
    global user
    r = requests.post('http://localhost:8000/queue', json={'secret':user['secret'], 'queueType':'vent'})
    assert(r.status_code == 200)
