import base64
import datetime
import os
from functools import wraps

import jwt
from bson import ObjectId
from flask import Blueprint, current_app, request

from lib.utils import error, expect_json, success

admin = Blueprint('admin', __name__)
jwt_secret = os.environ['JWT_SECRET']


# -------- AUTH STUFF --------
def requires_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        encoded_jwt = request.headers.get('authorization')
        if encoded_jwt is None:
            return error(403, "missing credentials")
        if validate_jwt(encoded_jwt):
            return f(*args, **kwargs)
        return error(403, "not cool enough for this club")

    return decorated_function


@admin.route("/auth", methods=["POST"])
@expect_json(password=str)
def admin_auth(body):
    if body['password'] == "ttmadmin":
        auth_token = {"authorization": generate_jwt()}
        return success(auth_token)
    return error(403, "Incorrect password")


# -------- ADMIN ENDPOINTS --------
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
    conversation = current_app.mdb.reported_messages.find({'room_id': room_id})
    data = []
    for x in conversation:
        x['_id'] = str(x['_id'])
        data.append(x)
    return success(data)


@admin.route("/banuser", methods=["POST"])
@requires_auth
@expect_json(report_id=str, reason=str)
def ban_user(body):
    report = current_app.mdb.reports.find_one({'_id': ObjectId(body['report_id'])})
    reported_user_ip = report['reported_ip']

    check = current_app.mdb.bannedUsers.count_documents({'ip': reported_user_ip})
    if check >= 1:
        return success("User already banned")

    ban_object = {
        "ip": reported_user_ip,
        "reason": body['reason'],
        "date": str(datetime.date.today())
    }
    current_app.mdb.bannedUsers.insert_one(ban_object)
    return success("Reported user banned")


@admin.route("/bannedusers", methods=["GET"])
@requires_auth
def get_banned_users():
    banned_users = current_app.mdb.bannedUsers.find()
    data = []
    for x in banned_users:
        x['_id'] = str(x['_id'])
        data.append(x)
    return success(data)


@admin.route("/unbanuser", methods=["POST"])
@requires_auth
@expect_json(ip=str)
def unban_user(body):
    current_app.mdb.bannedUsers.delete_one({"ip": body['ip']})
    return success("User unbanned")


# -------- MISC --------
def generate_jwt():
    encoded_jwt = jwt.encode({
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=10),
        'issued_time': datetime.datetime.utcnow().timestamp()
    }, jwt_secret).decode()
    return encoded_jwt


def validate_jwt(encoded_jwt):
    try:
        jwt.decode(encoded_jwt, jwt_secret)
        return True
    except jwt.DecodeError:
        return False
