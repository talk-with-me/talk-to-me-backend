from functools import wraps
from flask import Blueprint, current_app, Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_pymongo import PyMongo
from pymongo import MongoClient

import db
import os
import jwt
import json
import base64
import datetime
from bson import json_util, ObjectId
from lib import errors
from lib.utils import clean_json, error, expect_json, success

admin = Blueprint('admin', __name__)
jwt_secret = os.environ['JWT_SECRET']

# -------- AUTH STUFF --------
def requires_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            encoded_jwt = request.headers.get('authorization')
            if(validate_jwt(encoded_jwt)):
                return f(*args, **kwargs)
            return error(403, "not cool enough for this club")
        except:
            return error(403, "missing credentials")
    return decorated_function

@admin.route("/auth", methods=["POST"])
@expect_json(password=str)
def admin_auth(body):
    if(body['password'] == "ttmadmin"):
        auth_token = {"authorization" : generate_jwt()}
        return success(auth_token)
    return error(403, "Incorrect password")

# -------- ADMIN ENDPOINTS --------
# http://127.0.0.1:8000/admin/hello
@admin.route("/hello")
def hello():
    return "I think this blueprint works"

@admin.route("/reports", methods=["GET"])
@requires_auth
def get_reports():
    reports = current_app.mdb.reports.find()
    data = []
    for x in reports:
        x['_id'] = str(x['_id'])
        data.append(x)
    return success(data)

@admin.route("/reports/<room_id>/messages", methods=["GET"])
@requires_auth
def get_reported_messages(room_id):
    conversation = current_app.mdb.reported_messages.find({'room_id' : room_id})
    data=[]
    for x in conversation:
        x['_id'] = str(x['_id'])
        data.append(x)
    return success(data)

@admin.route("/banuser", methods=["POST"])
@requires_auth
@expect_json(room_id=str, reason=str)
def ban_user(body):
    report = current_app.mdb.reports.find_one({'room_id' : body['room_id']})
    reported_user_ip = report['reported_ip']
    
    check = current_app.mdb.bannedUsers.count_documents({'ip' : reported_user_ip})
    if (check >= 1):
        return success("User already banned")

    ban_object = {
        "ip" : reported_user_ip,
        "reason" : body['reason'],
        "date" : str(datetime.date.today())
    }
    current_app.mdb.bannedUsers.insert_one(ban_object)
    return success("Reported user banned")

@admin.route("/bannedusers", methods=["GET"])
@requires_auth
def get_banned_users():
    banned_users = current_app.mdb.bannedUsers.find()
    data=[]
    for x in banned_users:
        x['_id'] = str(x['_id'])
        data.append(x)
    return success(data)

@admin.route("/unbanuser", methods=["POST"])
@requires_auth
@expect_json(ip=str)
def unban_user(body):
    current_app.mdb.bannedUsers.delete_one({"ip" : body['ip']})
    return success("User unbanned")

# -------- MISC --------
def generate_jwt():
    encoded_jwt = jwt.encode({
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=10),
        'issued_time': datetime.datetime.utcnow().timestamp()
        }, jwt_secret)
    return base64.b64encode(encoded_jwt).decode('ascii')

def validate_jwt(encoded_jwt):
    try:
        encoded_jwt_bytes = base64.b64decode(encoded_jwt)
        jwt.decode(encoded_jwt_bytes, jwt_secret)
        return True
    except:
        return False
