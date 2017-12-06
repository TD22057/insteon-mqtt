#===========================================================================
#
# Modem commands
#
#===========================================================================
import paho.mqtt.client as mqtt
import random

_loop = True


def set_btn(args, config):
    id = random.getrandbits(32)

    client = mqtt.Client()
    if config["mqtt"].get("user", None):
        user = config["mqtt"]["user"]
        password = config["mqtt"].get("password", None)
        client.username_peq_set(user, password)

    client.connect(config["mqtt"]["broker"], config["mqtt"]["port"])

    rtn_topic = "%s/%s" % (args.cmd_topic, id)
    client.message_callback_add(rtn_topic, callback)
    client.subscribe(rtn_topic)

    topic = "%s/modem" % config["mqtt"]["cmd_topic"]
    payload = {
        "cmd" : "set_btn",
        "timeout" : args.timeout,
        "session" : id,
        }
    client.publish(topic, payload, qos=2)

    while _loop:
        mqtt.loop()


#===========================================================================
def callback(client, data, message):
    global _loop

    print("RECV:", message.payload.decode("utf-8"))
    _loop = False


#===========================================================================
