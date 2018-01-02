#===========================================================================
#
# Command line utilities
#
#===========================================================================
import json
import random
import time
import paho.mqtt.client as mqtt
from ..mqtt import Reply

TIME_OUT = 10  # seconds between messages


#===========================================================================
def send(config, topic, payload, quiet=False):
    session = {
        "result" : None,
        "done" : False,
        "status" : 0,
        "quiet" : quiet,
        }

    client = mqtt.Client(userdata=session)

    if config["mqtt"].get("user", None):
        user = config["mqtt"]["user"]
        password = config["mqtt"].get("password", None)
        client.username_pw_set(user, password)

    client.connect(config["mqtt"]["broker"], config["mqtt"]["port"])

    id = str(random.getrandbits(32))
    payload["session"] = id

    rtn_topic = "%s/session/%s" % (topic, id)
    client.message_callback_add(rtn_topic, callback)
    client.subscribe(rtn_topic)

    client.publish(topic, json.dumps(payload), qos=2)

    session["end_time"] = time.time() + TIME_OUT  # seconds
    while not session["done"] and time.time() < session["end_time"]:
        client.loop(timeout=0.5)

    if not session["done"]:
        print("Reply timed out")

    client.disconnect()
    return session


#===========================================================================
def callback(client, session, message):
    quiet = session["quiet"]

    session["end_time"] = time.time() + TIME_OUT

    msg = message.payload.decode("utf-8")
    reply = Reply.from_json(json.loads(msg))

    if reply.type == Reply.Type.END:
        session["done"] = True

    elif reply.type == Reply.Type.MESSAGE:
        if not quiet:
            print(reply.data)

    elif reply.type == Reply.Type.ERROR:
        session["status"] = -1
        if not quiet:
            print('ERROR:', reply.data)


#===========================================================================
