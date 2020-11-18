import datetime
import random
import time

import gpt_2_simple as gpt2
from bson import ObjectId

TYPING_SPEED = 60 / 500  # sec/char, based on average of 200cpm

sess = gpt2.start_tf_sess(threads=1)
gpt2.load_gpt2(sess, model_name='124M')


def schedule_reply_to_message(mdb, socketio, scheduler, content: str, room_id: str, user: dict):
    """
    When a user is banned, we want to handle any messages from them specially.

    Eventually some reply will be generated, so schedule sending a socket event with that reply.
    """
    if user.get('sid') is None:  # we're going to reply directly by session id, so if this is undefined just exit
        return

    # def do_reply():
    reply_content = generate_reply(content)
    reply_to_message(socketio, reply_content, user['sid'])

    # scheduler.add_job(do_reply,
    #                   trigger='date',
    #                   next_run_time=datetime.datetime.now())


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
    prompt = (
        f"You are a user talking to another user on a website designed for people to talk about their feelings.\n\n"
        f"User: Hello.\n"
        f"You: Hello! I am GPT-2.\n"
        f"User: {content}\n"
        f"You: "
    )

    reply = gpt2.generate(
        sess,
        prefix=prompt,
        include_prefix=False,
        model_name='124M',
        length=128
    )
    return reply[0]
