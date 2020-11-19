import datetime
import random
import time

from bson import ObjectId

TYPING_SPEED = 60 / 500  # sec/char, based on average of 200cpm


def schedule_reply_to_message(mdb, socketio, scheduler, content: str, room_id: str, user: dict):
    """
    When a user is banned, we want to handle any messages from them specially.

    Eventually some reply will be generated, so schedule sending a socket event with that reply.
    """
    if user.get('sid') is None:  # we're going to reply directly by session id, so if this is undefined just exit
        return
    reply_content = generate_reply(content)
    reply_time = datetime.datetime.now() + datetime.timedelta(seconds=TYPING_SPEED * len(reply_content))
    scheduler.add_job(reply_to_message,
                      trigger='date',
                      next_run_time=reply_time,
                      kwargs={"socketio": socketio, "content": reply_content, "user_sid": user['sid']})


def reply_to_message(socketio, content, user_sid):
    """
    Sends a socketio event to a client containing some artificial message.
    """
    message = {
        "_id": str(ObjectId()),
        "room_id": user_sid,
        "author": 'beepboopimabot',
        "timestamp": time.time(),
        "nonce": f'beepboopimabot-{random.random()}',
        "content": content,
        "liked": False
    }
    socketio.emit('send_message_to_client', message, room=user_sid)


def generate_reply(content: str):
    """
    Generates a reply to some message.
    """
    return content  # currently, just echo
