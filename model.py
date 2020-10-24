# This is pseudocode - WILL NOT COMPILE


# insert Alex's db

class User(db) :
    ip = db.Column(db.String())
    id = db.Column(db.String())
    secret = db.Column(db.Integer, primary_key = True)
    inQueue = db.Column(db.Boolean())
    queueType = db.Column(db.String())
    enteredQueueAt = db.Column(db.timestamp) #???