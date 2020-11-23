import datetime
import random
import time

import torch
from bson import ObjectId
from transformers import AutoModelWithLMHead, AutoTokenizer

TYPING_SPEED = 60 / 500  # sec/char, based on average of 200cpm

tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-medium", cache_dir='models')
model = AutoModelWithLMHead.from_pretrained("microsoft/DialoGPT-medium", cache_dir='models')


def schedule_reply_to_message(mdb, socketio, scheduler, content: str, room_id: str, user: dict):
    """
    When a user is banned, we want to handle any messages from them specially.

    Eventually some reply will be generated, so schedule sending a socket event with that reply.
    """
    if user.get('sid') is None:  # we're going to reply directly by session id, so if this is undefined just exit
        return

    def do_reply():
        history = get_ai_chat_history(mdb, user['sid'], history_len=1)
        reply_content, history_tensor = generate_reply(content, history)
        save_ai_chat_history(mdb, user['sid'], history_tensor, content, reply_content)
        # time.sleep(TYPING_SPEED * len(reply_content))
        reply_to_message(socketio, reply_content, user['sid'])

    scheduler.add_job(do_reply,
                      trigger='date',
                      next_run_time=datetime.datetime.now())


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


def generate_reply(content: str, history_tensor: torch.LongTensor = None):
    """
    Generates a reply to some message.
    """
    if history_tensor is None:
        history_tensor = torch.LongTensor([])

    # encode the new user input, add the eos_token and return a tensor in Pytorch
    new_user_input_ids = tokenizer.encode(content + tokenizer.eos_token, return_tensors='pt')

    # append the new user input tokens to the chat history
    # todo fix history
    bot_input_ids = new_user_input_ids  # torch.cat([history_tensor, new_user_input_ids], dim=-1)

    # generated a response while limiting the total chat history to 128 tokens,
    chat_history_ids = model.generate(bot_input_ids, max_length=128 + bot_input_ids.shape[-1],
                                      pad_token_id=tokenizer.eos_token_id)
    response_ids = chat_history_ids[:, bot_input_ids.shape[-1]:]

    # pretty print last ouput tokens from bot
    result = tokenizer.decode(response_ids[0], skip_special_tokens=True)

    return result, torch.cat([new_user_input_ids, response_ids], dim=-1)


def get_ai_chat_history(mdb, user_id, history_len=2):
    # get the chat history from mongo
    chat_history_doc = mdb.ai_messages.find_one({"sid": user_id})
    if chat_history_doc is None:
        return torch.LongTensor([])
    else:
        chat_history = chat_history_doc['chat_history_tensors'][-history_len:]
        return torch.cat([torch.LongTensor(h) for h in chat_history], dim=-1)


def save_ai_chat_history(mdb, user_id, chat_history_tensor, content, result):
    # save the history
    history_list = chat_history_tensor.tolist()

    mdb.ai_messages.update_one(
        {"sid": user_id},
        {"$push": {"chat_history_text": {"$each": [f"User: {content}", f"AI: {result}"]},
                   "chat_history_tensors": history_list}},
        upsert=True
    )
