import datetime
import random
import time

from bson import ObjectId
from gpt2_client import GPT2Client

TYPING_SPEED = 60 / 500  # sec/char, based on average of 200cpm

gpt2 = GPT2Client('117M')  # this depends on the model already being downloaded


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
    reply = gpt2.generate_batch_from_prompts([
        f"You are a user talking to another user on a website designed for people to talk about their feelings.\n\n"
        f"User: Hello.\n"
        f"You: Hello! I am GPT-2.\n"
        f"User: {content}\n"
    ])
    return reply[0]
