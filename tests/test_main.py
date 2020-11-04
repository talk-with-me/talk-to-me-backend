# test_main.py - main test file for talk-to-me backend server
import pytest
import requests

user = ''

def test_get_auth():
    global user
    r = requests.get('http://localhost:8000/auth')
    user = r.json()['data']
    assert(r.status_code == 200)

def test_bad_select():
    r = requests.post('http://localhost:8000/queue', json={"secret":"fender"})
    assert(r.status_code == 403)

def test_good_select():
    global users
    r = requests.post('http://localhost:8000/queue', json={"secret":user['secret']})
    assert(r.status_code == 200)
