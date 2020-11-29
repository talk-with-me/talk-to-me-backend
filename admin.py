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

app = Flask(__name__)
app.config["SECRET_KEY"] = "ttmadmin"
CORS(app)
mdb = MongoClient(db.MONGO_URL).db

@app.route("/auth", methods=["POST"])
@expect_json(password=str)
def admin_auth(body):
    if(body['password'] == "ttmadmin"):
        return success("Authorized")
    return error(403, "Incorrect password")

@app.route("/reports", methods=["GET"])
def get_reports():
    reports = mdb.reports.find()
    data=[]
    for x in reports:
        x['_id'] = str(x['_id'])
        data.append(x)
    jsonData=json.dumps(data)
    return jsonData

@app.route("/reportmessages", methods=["POST"])
@expect_json(room_id=str)
def get_reported_messages(body):
    conversation = mdb.reported_messages.find({'room_id' : body['room_id']})
    data=[]
    for x in conversation:
        x['_id'] = str(x['_id'])
        data.append(x)
    jsonData=json.dumps(data)
    return jsonData

@app.route("/banuser", methods=["POST"])
@expect_json(room_id=str, reason=str)
def ban_user(body):
    report = mdb.reports.find_one({'room_id' : body['room_id']})
    reported_user_ip = report['reported_ip']
    ban_object = {
        "ip" : reported_user_ip,
        "reason" : body['reason'],
        "date" : datetime.date.today()
    }
    mdb.bannedUsers.add(ban_object)
    return success(200, "Reported user banned")

@app.route("/bannedusers", methods=["GET"])
def get_banned_users():
    banned_users = mdb.bannedUsers.find()
    data=[]
    for x in banned_users:
        x['_id'] = str(x['_id'])
        data.append(x)
    jsonData=json.dumps(data)
    return jsonData

@app.route("/unbanuser", methods=["POST"])
@expect_json(ip=str)
def unban_user(body):
    mdb.bannedUsers.delete_one({"ip" : body['ip']})
    return success(200, "User unbanned")

if __name__ == "__main__":
    app.run(port=6000, host="0.0.0.0")