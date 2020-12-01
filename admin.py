from functools import wraps
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_pymongo import PyMongo
from pymongo import MongoClient

import db
import json
import datetime
from bson import json_util, ObjectId
from lib import errors
from lib.utils import clean_json, error, expect_json, success

admin = Flask(__name__)
admin.config["SECRET_KEY"] = "ttmadmin"
CORS(admin)
mdb = MongoClient(db.MONGO_URL).db

def requires_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('authorization')
        if(token != "ttmadmin"):
            return error(403, "Unauthorized")
        return f(*args, **kwargs)
    return decorated_function

@admin.route("/reports", methods=["GET"])
@requires_auth
def get_reports():
    reports = mdb.reports.find()
    data=[]
    for x in reports:
        x['_id'] = str(x['_id'])
        data.append(x)
    jsonData=json.dumps(data)
    return success(jsonData)

@admin.route("/reports/<room_id>/messages", methods=["GET"])
@requires_auth
def get_reported_messages(room_id):
    conversation = mdb.reported_messages.find({'room_id' : room_id})
    data=[]
    for x in conversation:
        x['_id'] = str(x['_id'])
        data.append(x)
    jsonData=json.dumps(data)
    return success(jsonData)

@admin.route("/banuser", methods=["POST"])
@requires_auth
@expect_json(room_id=str, reason=str)
def ban_user(body):
    report = mdb.reports.find_one({'room_id' : body['room_id']})
    reported_user_ip = report['reported_ip']
    
    check = mdb.bannedUsers.count_documents({'ip' : reported_user_ip})
    if (check >= 1):
        return success("User already banned")

    ban_object = {
        "ip" : reported_user_ip,
        "reason" : body['reason'],
        "date" : str(datetime.date.today())
    }
    mdb.bannedUsers.insert_one(ban_object)
    return success("Reported user banned")

@admin.route("/bannedusers", methods=["GET"])
@requires_auth
def get_banned_users():
    banned_users = mdb.bannedUsers.find()
    data=[]
    for x in banned_users:
        x['_id'] = str(x['_id'])
        data.append(x)
    jsonData=json.dumps(data)
    return success(jsonData)

@admin.route("/unbanuser", methods=["POST"])
@requires_auth
@expect_json(ip=str)
def unban_user(body):
    mdb.bannedUsers.delete_one({"ip" : body['ip']})
    return success("User unbanned")

if __name__ == "__main__":
    admin.run(port=6000, host="0.0.0.0")