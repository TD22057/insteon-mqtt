#===========================================================================
#
# Device commands
#
#===========================================================================
import json
import paho.mqtt.client as mqtt
import random
import time

_loop = True


#===========================================================================
def on(args, config):
    id = random.getrandbits(32)

    client = mqtt.Client()
    if config["mqtt"].get("user", None):
        user = config["mqtt"]["user"]
        password = config["mqtt"].get("password", None)
        client.username_pw_set(user, password)

    client.connect(config["mqtt"]["broker"], config["mqtt"]["port"])

    rtn_topic = "%s/RTN/%s" % (args.topic, id)
    client.message_callback_add(rtn_topic, callback)
    client.subscribe(rtn_topic)

    topic = "%s/%s" % (args.topic, args.address)
    payload = {
        "cmd" : "on",
        "level" : args.level,
        "instant" : args.instant,
        "session" : id,
        }
    client.publish(topic, json.dumps(payload), qos=2)

    end = time.time() + 10
    while _loop and time.time() < end:
        client.loop()

    if _loop:
        print("Reply timed out")


#===========================================================================
def off(args, config):
    id = random.getrandbits(32)

    client = mqtt.Client()
    if config["mqtt"].get("user", None):
        user = config["mqtt"]["user"]
        password = config["mqtt"].get("password", None)
        client.username_pw_set(user, password)

    client.connect(config["mqtt"]["broker"], config["mqtt"]["port"])

    rtn_topic = "%s/RTN/%s" % (args.topic, id)
    client.message_callback_add(rtn_topic, callback)
    client.subscribe(rtn_topic)

    topic = "%s/%s" % (args.topic, args.address)
    payload = {
        "cmd" : "off",
        "instant" : args.instant,
        "session" : id,
        }
    client.publish(topic, json.dumps(payload), qos=2)

    end = time.time() + 10
    while _loop and time.time() < end:
        client.loop()

    if _loop:
        print("Reply timed out")


#===========================================================================
def callback(client, data, message):
    global _loop

    print("RECV:",message.payload.decode("utf-8"))
    _loop = False


#===========================================================================
