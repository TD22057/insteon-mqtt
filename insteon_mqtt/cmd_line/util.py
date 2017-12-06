#===========================================================================
#
# Command line utilities
#
#===========================================================================
import json
import random
import time
import paho.mqtt.client as mqtt


#===========================================================================
def send(config, topic, payload, on_message=None, on_done=None):
    session = {
        "replies" : [],
        "result" : None,
        "done" : False,
        }

    client = mqtt.Client(userdata=session)

    if config["mqtt"].get("user", None):
        user = config["mqtt"]["user"]
        password = config["mqtt"].get("password", None)
        client.username_pw_set(user, password)

    client.connect(config["mqtt"]["broker"], config["mqtt"]["port"])
    if on_message:
        client.on_message = on_message

    id = str(random.getrandbits(32))
    payload["session"] = id

    rtn_topic = "%s/RTN/%s" % (topic, id)
    client.message_callback_add(rtn_topic, callback)
    client.subscribe(rtn_topic)

    client.publish(topic, json.dumps(payload), qos=2)

    end = time.time() + 3  # TODO: timeout?
    while not session["done"] and time.time() < end:
        client.loop(timeout=0.5)

    if not session["done"]:
        print("Reply timed out")

    if on_done:
        on_done(session)

    client.disconnect()
    return session


#===========================================================================
def callback(client, session, message):
    msg = message.payload.decode("utf-8")
    print("RECV:", msg)

    data = json.loads(msg)
    session["replies"].append(data)

    session["done"] = False

#===========================================================================
