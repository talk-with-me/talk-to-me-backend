# app,py - main file for talk-to-me backend
# TADAA, Oct 2020

import atexit
import time
import uuid

from apscheduler.schedulers.background import BackgroundScheduler
from bson import ObjectId
from flask import Flask, request
from flask_cors import CORS
from flask_socketio import SocketIO, join_room, leave_room
from pymongo import MongoClient
import eventlet

import db
from admin import admin
from lib import errors
from lib.utils import clean_json, error, expect_json, success

# start app
eventlet.monkey_patch(thread=True, time=True)
app = Flask(__name__)
app.config["SECRET_KEY"] = "ttm"
CORS(app)
app.mdb = mdb = MongoClient(db.MONGO_URL).db
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)
scheduler = BackgroundScheduler()


# ===== REST =====
@app.route("/queue", methods=["POST"])
def request_queue():
    """Generates user info and places them into a queue, returning info"""
    print('queue received')

    user_ip = request.headers.get('X-Real-Ip', request.remote_addr)
    user_id = str(uuid.uuid4())
    user_secret = str(uuid.uuid4())
    user_object = {
        "ip": user_ip,
        "user_id": user_id,
        "secret": user_secret,
        "queueType": "banned" if ip_is_banned(user_ip) else "searching",
        "time": time.time(),
        "room": "none",
        "sid": None,
    }

    mdb.users.insert_one(user_object)

    return success({"id": user_id, "secret": user_secret})

@app.route("/test", methods=["POST"])
def test_emit():
    print('EMITTING TEST')
    socketio.emit('test', {'manual':'test'})
    return success('success!')

@app.route("/test_room", methods=["POST"])
@expect_json(room=str)
def test_emit_room(json_body):
    room = json_body['room']
    print('EMITTING TEST TO ROOM', room)
    socketio.emit('test', {'manual':'test_room'}, room=room)
    return success('success!')

@app.route("/typing", methods=["POST"])
@expect_json(user_id=str, secret=str, typing=bool)
def handle_typing(json_body):
    """User starts/stop typing"""
    author_obj = mdb.users.find_one({"user_id": json_body["user_id"], "secret": json_body["secret"]})
    
    if author_obj is None:
        return error(403, "user not found")

    recipient_obj = mdb.users.find_one({"room": author_obj["room"], "user_id": {"$ne": author_obj["user_id"]}})

    if recipient_obj is None:
        return error(403, "user(s) not found")

    if typing:
        socketio.emit("partner_starts_typing",
                room=recipient_obj["sid"])
    else:
        socketio.emit("partner_stops_typing",
                room=recipient_obj["sid"])

    return success("partner starting typing" if typing else "partner stopped typing", 201)

@app.route("/messages", methods=["POST"])
@expect_json(message_id=str, user_id=str, secret=str, content=str)
def handle_message(json_body):
    """User sends message."""
    author_obj = mdb.users.find_one({"user_id": json_body["user_id"], "secret": json_body["secret"]})
    
    if author_obj is None:
        return error(403, "user not found")

    recipient_obj = mdb.users.find_one({"room": author_obj["room"], "user_id": {"$ne": author_obj["user_id"]}})

    if recipient_obj is None:
        return error(403, "user(s) not found")

    message = {
        "room_id": author_obj["room"],
        "author": author_obj["user_id"],
        "recipient": recipient_obj["user_id"],
        "timestamp": time.time(),
        "message_id": json_body["message_id"],
        "content": json_body["content"],
        "liked": False,
    }

    # otherwise handle the message as normal
    mdb.messages.insert_one(message)

    socketio.emit("send_message_to_client",
            clean_json({
                "message_id": json_body["message_id"],
                "incoming": True,
                "content": json_body["content"],
                "liked": False,
            }),
            room=recipient_obj["sid"])

    return success(message, 201)


@app.route("/likes", methods=["POST"])
@expect_json(secret=str, message_id=str)
def handle_message_like(body):
    """User likes message."""
    user = mdb.users.find_one({"secret": body["secret"]})
    if user is None:
        return error(403, "user not found")
    room_id = user["room"]
    message_id = body["message_id"]
    print(f"Liking message {message_id}")
    mdb.messages.update_one({"_id": ObjectId(message_id)},
                            {"$set": {"liked": True}})
    socketio.emit(
        "message_liked",
        {"message_id": message_id, "user_id": user["user_id"]},
        room=room_id,
    )
    return success("message liked", 200)


@app.route("/reports", methods=["POST"])
@expect_json(secret=str, reason=str)
def handle_report(body):
    """User reports conversation."""
    user = mdb.users.find_one({"secret": body["secret"]})
    if user is None:
        return error(404, "user who clicked on report not found")
    room_obj = mdb.rooms.find_one({"room": user["room"]})

    if room_obj["user1"] == user["user_id"]:
        reported_user_id = room_obj["user2"]
        reported_user_ip = mdb.users.find_one(
            {"user_id": reported_user_id}, {"ip": 1, "_id": 0}
        )
        reporter_user_ip = mdb.users.find_one(
            {"user_id": room_obj["user1"]}, {"ip": 1, "_id": 0}
        )

    else:
        reported_user_id = room_obj["user1"]
        reported_user_ip = mdb.users.find_one(
            {"user_id": reported_user_id}, {"ip": 1, "_id": 0}
        )
        reporter_user_ip = mdb.users.find_one(
            {"user_id": room_obj["user2"]}, {"ip": 1, "_id": 0}
        )

    # insert a Report object into a reports collection
    mdb.reports.insert_one(
        {
            "reporter": user["user_id"],
            "reporter_ip": reporter_user_ip["ip"],
            "reported": reported_user_id,
            "reported_ip": reported_user_ip["ip"],
            "reason": body["reason"],
            "room_id": room_obj["room"],
        }
    )

    # copy all message objs in reported conversation to the other collection
    reported_conversation = mdb.messages.find({"room_id": room_obj["room"]})
    mdb.reported_messages.insert_many(list(reported_conversation))
    return success("conversation reported", 200)


def delete_user_from_db(user_obj):
    """Delete user_obj from all collections."""
    mdb.users.delete_one({"secret": user_obj["secret"]})
    mdb.messages.delete_many({"author": user_obj["user_id"]})
    mdb.rooms.delete_one({"room": user_obj["room"]})


def check_users_in_room(room_id):
    """Check that both users left room before deleting room."""
    room_obj = mdb.rooms.find_one({"room": room_id})
    if room_obj is None:
        print("bad room, not found")
        return

    # at least 1 user disconnected, so this is the 2nd user
    if room_obj["disconnected"] >= 1:
        user1 = mdb.users.find_one({"user_id": room_obj["user1"]})
        user2 = mdb.users.find_one({"user_id": room_obj["user2"]})
        delete_user_from_db(user1)
        delete_user_from_db(user2)
    else:
        mdb.rooms.update_one({"room": room_id}, {"$set": {"disconnected": 1}})


# ====== SOCKET STUFF =====
@socketio.on("connect")
def user_connect():
    print('user connected!')

@socketio.on("join_room")
def user_join_room(secret):
    """Socket event to have user actually join the room."""
    user_obj = mdb.users.find_one({"secret": secret})  # fetch user
    if user_obj is None:
        print("bad user not found")
        return
    join_room(user_obj["room"])
    print(user_obj["user_id"] + " has joined room " + user_obj["room"])


@socketio.on("register_sid")
def user_sid_assoc(secret):
    """Associates a SocketIO session ID with a user object."""
    print('registering', request.sid, 'with secret', secret)

    user = mdb.users.find_one({"secret": secret})  # fetch user from db
    if user is None:
        print("user_sid_assoc: user not found")
        return

    # noinspection PyUnresolvedReferences
    # provided by socketio
    sid = request.sid

    # Join room so can be privately communicated to by server via emit to room
    join_room(request.sid)

    print(f"User {user['user_id']} has socket session ID" + sid)
    mdb.users.update_one({"secret": secret}, {"$set": {"sid": sid}})
    return


@socketio.on("leave_room")
def user_leave_room(secret):
    """User leaves room."""
    user_obj = mdb.users.find_one({"secret": secret})  # fetch user
    if user_obj is None:
        print("bad user not found")
        return
    if user_obj['room'] != 'lonely':  # only emit if the user is in a room
        leave_room(user_obj["room"])
        socketio.emit("user_disconnected", room=user_obj["room"])
    if user_obj["queueType"] == "banned":
        delete_user_from_db(user_obj)
    elif user_obj["room"] == "lonely":
        delete_user_from_db(user_obj)
    else:
        check_users_in_room(user_obj["room"])
    print(user_obj["user_id"] + " has left room " + user_obj["room"])


@socketio.on("disconnect")
def user_disconnect():  # ensure that eventlet is installed!!
    """User disconnects from app."""
    user_obj = mdb.users.find_one({"sid": request.sid})  # fetch user
    if user_obj is None:
        return

    if user_obj['room'] != 'lonely':  # only emit if the user is in a room
        socketio.emit("user_disconnected", room=user_obj["room"])

    # check to see if user disconnected while in room or in a queue
    if user_obj["queueType"] == "outQueue":
        check_users_in_room(user_obj["room"])
    else:
        delete_user_from_db(user_obj)
    print("yay user has been deleted")


# ===== MISC =====
# register handlers and stuff
errors.register_error_handlers(app)


# ===== DEV ONLY ====
def ip_is_banned(user_ip):
    """Checks if user is banned."""
    if mdb.bannedUsers.find_one({"ip": user_ip}) is None:
        return False
    else:
        return True


def notify_queue_complete(users):
    """Broadcast that room is ready to be joined for users."""
    for user in users:
        user_id = user['user_id']
        print('Notifying', user_id, 'that queue is complete')
        socketio.emit('queue_complete', user, room=user['sid'])


def put_users_in_room(users):
    """Puts two users into a room."""
    room_id = str(uuid.uuid4())
    user1 = users[0]
    user2 = users[1]
    mdb.rooms.insert_one(
        {"room": room_id, "user1": user1, "user2": user2,
         "disconnected": 0}
    )
    mdb.users.update_one(
        {"user_id": user1['user_id']},
        {"$set": {"room": room_id, "queueType": "out"}}
    )
    mdb.users.update_one(
        {"user_id": user2['user_id']},
        {"$set": {"room": room_id, "queueType": "out"}}
    )
    print(
        "user "
        + user1['user_id']
        + " and user "
        + user2['user_id']
        + " have been assigned room "
        + room_id
    )

def check_queue():
    """Matches two people in queue together and broadcasts the socket
    event to both"""
    print('checking queue...')
    count_talk = mdb.users.count_documents({"queueType": "searching"})
    if count_talk >= 2:
        # this should find the first two people in the queue
        query = mdb.users.find(
                {"queueType": "searching", "room": "none"}, {"user_id": 1, "sid": 1, "_id": 0}
        ).limit(2)
        users = []
        for x in query:
            users.append(x)
        # print(users)
        put_users_in_room(users)
        # pass user_id to notify_queue_complete()
        notify_queue_complete(users)

# APScheduler running in background
scheduler.add_job(
    func=check_queue,
    trigger="interval",
    seconds=1,
    id="check_is_queue_ready",
    name="Check queue status every 1 seconds",
    replace_existing=True,
)

scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

app.register_blueprint(admin, url_prefix="/admin")

if __name__ == "__main__":
    socketio.run(app, port=8000, host="localhost")
