# app,py - main file for talk-to-me backend
# TADAA, Oct 2020

# import flask stuff
from flask import Flask, render_template, redirect, url_for, jsonify, \
        request, Response
from flask_cors import CORS
from flask_socketio import SocketIO, send, join_room, leave_room
from flask_pymongo import PyMongo

# import config
from pymongo import MongoClient

# import general stuff
import db
import os
import sys
import uuid
import time
import json
import random
import atexit
import datetime
from bson import json_util, ObjectId
from lib import errors
from lib.utils import clean_json, error, expect_json, success
import bot.replier

# import async stuff
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

# start app
app = Flask(__name__)
app.config["SECRET_KEY"] = "ttm"
CORS(app)
mdb = MongoClient(db.MONGO_URL).db
socketio = SocketIO(app, cors_allowed_origins="*")
scheduler = BackgroundScheduler()


# ===== REST =====
@app.route("/auth", methods=["GET"])
def user_auth():
    """Generates an id and secret for the user, stores them and returns them
    to user.
    """
    user_id = str(uuid.uuid4())
    user_secret = str(uuid.uuid4())
    user_obj = {
        "ip": request.remote_addr,
        "user_id": user_id,
        "secret": user_secret,
        "queueType": "idle",
        "time": time.time(),
        "room": "lonely",
        "sid": None,
    }

    if is_banned(user_obj["ip"]):
        user_obj["queueType"] = "banned"

    mdb.userDetails.insert_one(user_obj)
    return success(user_obj)


@app.route("/queue", methods=["POST"])
@expect_json(secret=str, queueType=str)
def request_queue(body):
    """User chooses queueType."""
    user_object = mdb.userDetails.find_one(
        {"secret": body["secret"]}          # Fetches user from db
    )
    if user_object is not None:
        if user_object["queueType"] == "banned":
            return success("sike, you banned")
        elif (user_object["queueType"] != "idle" or
                user_object["room"] != "lonely"):
            return error(403, "nah you already in queue or in a room")

        mdb.userDetails.update_one(
            {"secret": body["secret"]},
            {"$set": {"queueType": body["queueType"], "time": time.time()}},
        )
        return success("you have been placed in queue")
    return error(403, "go do auth first you dummy")


@app.route("/messages", methods=["POST"])
@expect_json(secret=str, message=str, nonce=str)
def handle_message(jsonObj):
    """User sends message."""
    user_obj = mdb.userDetails.find_one({"secret": jsonObj["secret"]})
    if user_obj is None:
        return error(403, "do auth first you dummy")
    room_id = user_obj["room"]
    user_id = user_obj["user_id"]
    print("Message: " + jsonObj["message"])
    message = {
        # _id autogenerated
        "room_id": room_id,
        "author": user_id,
        "timestamp": time.time(),
        "nonce": jsonObj["nonce"],
        "content": jsonObj["message"],
        "liked": False,
    }

    # if the user is banned, hand their message off to a bot
    # noinspection PyUnreachableCode
    if True:  # todo: if user_is_banned()
        bot.replier.schedule_reply_to_message(
            mdb,
            socketio,
            scheduler,
            content=jsonObj["message"],
            room_id=room_id,
            user=user_obj,
        )
        return success(message, 201)

    # otherwise handle the message as normal
    mdb.messages.insert_one(message)
    socketio.emit("send_message_to_client", clean_json(message), room=room_id)
    return success(message, 201)


@app.route("/likes", methods=["POST"])
@expect_json(secret=str, message_id=str)
def handle_message_like(body):
    """User likes message."""
    user = mdb.userDetails.find_one({"secret": body["secret"]})
    if user is None:
        return error(403, "do auth first you dummy")
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
    user = mdb.userDetails.find_one({"secret": body["secret"]})
    if user is None:
        return error(404, "user who clicked on report not found")
    room_obj = mdb.rooms.find_one({"room": user["room"]})

    if room_obj["user1"] == user["user_id"]:
        reported_user_id = room_obj["user2"]
        reported_user_ip = mdb.userDetails.find_one(
            {"user_id": reported_user_id}, {"ip": 1, "_id": 0}
        )
        reporter_user_ip = mdb.userDetails.find_one(
            {"user_id": room_obj["user1"]}, {"ip": 1, "_id": 0}
        )

    else:
        reported_user_id = room_obj["user1"]
        reported_user_ip = mdb.userDetails.find_one(
            {"user_id": reported_user_id}, {"ip": 1, "_id": 0}
        )
        reporter_user_ip = mdb.userDetails.find_one(
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
    mdb.userDetails.delete_one({"secret": user_obj["secret"]})
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
        user1 = mdb.userDetails.find_one({"user_id": room_obj["user1"]})
        user2 = mdb.userDetails.find_one({"user_id": room_obj["user2"]})
        delete_user_from_db(user1)
        delete_user_from_db(user2)
    else:
        mdb.rooms.update_one({"room": room_id}, {"$set": {"disconnected": 1}})


# ====== SOCKET STUFF =====
@socketio.on("join_room")
def user_join_room(secret):
    """Socket event to have user actually join the room."""
    user_obj = mdb.userDetails.find_one({"secret": secret})  # fetch user
    if user_obj is None:
        print("bad user not found")
        return
    join_room(user_obj["room"])
    socketio.emit("user_connected", room=user_obj["room"])
    print(user_obj["user_id"] + " has joined room " + user_obj["room"])


@socketio.on("hello")
def user_sid_assoc(secret):
    """Associates a SocketIO session ID with a user object."""
    user = mdb.userDetails.find_one({"secret": secret})  # fetch user from db
    if user is None:
        print("user_sid_assoc: user not found")
        return
    # noinspection PyUnresolvedReferences
    # provided by socketio
    sid = request.sid
    mdb.userDetails.update_one({"secret": secret}, {"$set": {"sid": sid}})
    print("User {user['user_id']} has socket session ID" + sid)


@socketio.on("leave_room")
def user_leave_room(secret):
    """User leaves room."""
    user_obj = mdb.userDetails.find_one({"secret": secret})  # fetch user
    if user_obj is None:
        print("bad user not found")
        return
    # todo whatever teardown you need
    leave_room(user_obj["room"])
    socketio.emit("user_disconnected", room=user_obj["room"])
    check_users_in_room(user_obj["room"])
    print(user_obj["user_id"] + " has left room " + user_obj["room"])


@socketio.on("disconnect")
def user_disconnect():  # ensure that eventlet is installed!!
    """User disconnects from app."""
    user_obj = mdb.userDetails.find_one({"sid": request.sid})  # fetch user
    if (
        user_obj is None
    ):  # still not sure why this would happen but here's protection in case
        return
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


def is_banned(user_ip):
    """Checks if user is banned."""
    if mdb.bannedUsers.find_one({"ip": user_ip}) is None:
        return False
    else:
        return True


def notify_queue_complete(user_id):
    """Broadcast that room is ready to be joined for two users."""
    socketio.emit("queue_complete", {"user_id": user_id[0]})
    socketio.emit("queue_complete", {"user_id": user_id[1]})


def match_making(user_ids):
    """Matchmaking algorithm, ran in background."""
    roomID = str(uuid.uuid4())
    user_ID1 = user_ids[0]
    user_ID2 = user_ids[1]
    mdb.rooms.insert_one(
        {"room": roomID, "user1": user_ID1, "user2": user_ID2,
            "disconnected": 0}
    )
    mdb.userDetails.update_one(
        {"user_id": user_ID1},
        {"$set": {"room": roomID, "queueType": "outQueue"}}
    )
    mdb.userDetails.update_one(
        {"user_id": user_ID2},
        {"$set": {"room": roomID, "queueType": "outQueue"}}
    )
    print(
        "user "
        + user_ID1
        + " and user "
        + user_ID2
        + " have been assigned room "
        + roomID
    )


def find_time_difference(userTime):
    """See if enough time passed to go to fall back queue(talk)."""
    difference = time.time() - userTime
    return int(difference) > 10


def change_vent_listen_to_talk(query):
    """Change user queueType from listen to talk"""
    for x in query:
        if find_time_difference(x["time"]):
            mdb.userDetails.update_one(
                {"secret": x["secret"]}, {"$set": {"queueType": "talk"}}
            )


def check_queue():
    """Matches vent with listen (vice versa), matches talk with talk
    keeps in one collection instead of multiple for each queueType
    problematic if large number of people.
    """
    countVent = mdb.userDetails.count_documents({"queueType": "vent"})
    countListen = mdb.userDetails.count_documents({"queueType": "listen"})

    # --------MATCH MAKING FOR VENT OR LISTEN----------

    # at least 1 person in either vent or listen
    if (countVent + countListen) > 0:
        # at least 1 person in vent AND listen, so match them
        if countVent >= 1 & countListen >= 1:
            getVent = mdb.userDetails.find_one({"queueType": "vent"})
            getListen = mdb.userDetails.find_one({"queueType": "listen"})

            # if someone leaves the queue at this moment
            # there might be a better way to write this case
            if getVent is None or getListen is None:
                return

            user_ids = []
            user_ids.append(getVent["user_id"])
            user_ids.append(getListen["user_id"])

            match_making(user_ids)
            notify_queue_complete(user_ids)
        # means 1 person or more in either vent/listen and no one in the other
        # checks if they been waiting too long and changes them to talk
        else:
            if countListen == 0:  # no one in listen
                queryVent = mdb.userDetails.find(
                    {"queueType": "vent"}, {"time": 1, "secret": 1, "_id": 0}
                )
                change_vent_listen_to_talk(queryVent)
            else:  # no one in vent
                queryListen = mdb.userDetails.find(
                    {"queueType": "listen"}, {"time": 1, "secret": 1, "_id": 0}
                )
                change_vent_listen_to_talk(queryListen)

    # ------------MATCH MAKING FOR TALK--------------
    # matchmaking for talk (same as isQueueReady)
    countTalk = mdb.userDetails.count_documents({"queueType": "talk"})
    if countTalk >= 2:
        # this should find the first two people in the queue
        query = mdb.userDetails.find(
            {"queueType": "talk"}, {"user_id": 1, "secret": 1, "_id": 0}
        ).limit(2)
        user_ids = []
        for x in query:
            user_ids.append(x["user_id"])
        match_making(user_ids)
        # pass user_id to notify_queue_complete()
        notify_queue_complete(user_ids)


# -----------------MAKE SURE TO REMOVE THESE ON RELEASE---------------------
@app.route("/deleteUserDetails")
def delete_user_details():
    """Deletes all documents in UserDetails."""
    mdb.userDetails.delete_many({})
    return "deleted all docs in userDetails"


@app.route("/deleteRoomDetails")
def delete_room_details():
    """Deletes all rooms."""
    mdb.rooms.delete_many({})
    return "deleted all docs in rooms"


@app.route("/deleteMessageDetails")
def delete_message_details():
    """Deletes all messages."""
    mdb.messages.delete_many({})
    return "deleted all docs in messages"


@app.route("/deleteAllDetails")
def delete_all_details():
    """Nukes the database."""
    mdb.userDetails.delete_many({})
    mdb.rooms.delete_many({})
    mdb.messages.delete_many({})
    mdb.reported_messages.delete_many({})
    mdb.reports.delete_many({})
    mdb.bannedUsers.delete_many({})
    return "all gone!"


# APScheduler running in background
scheduler.add_job(
    func=check_queue,
    trigger="interval",
    seconds=3,
    id="check_is_queue_ready",
    name="Check queue status every 3 seconds",
    replace_existing=True,
)
scheduler.start()
# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

if __name__ == "__main__":
    socketio.run(app, port=8000, host="0.0.0.0")
