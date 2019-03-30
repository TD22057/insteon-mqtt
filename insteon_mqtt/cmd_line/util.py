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

# Time between messages before we decide that the something went wrong and
# stop.  Currently the server should send enough messages to avoid this but
# there is no pure right answer for what this should be.
TIME_OUT = 10


#===========================================================================
def send(config, topic, payload, quiet=False):
    """Send a message and get the replies from the server.

    Args:
      config:   (dict) Configuration dictionary.  The MQTT broker and
                connection information is read from this.
      topic:    (str) The MQTT topic string.
      payload:  (dict) Message payload dictionary.  Will be converted to json.
      quiet:    0: show all messages.  1: show no messages.  2: show only
                the reply messages.

    Returns:
      Returns the session reply object.  This is a dict with the results of the
      command.
    """
    session = {
        "result" : None,
        "done" : False,
        "status" : 0,  # 0 == success
        "quiet" : int(quiet),
        }

    client = mqtt.Client(userdata=session)

    # Add user/password if the config file has them set.
    if config["mqtt"].get("username", None):
        user = config["mqtt"]["username"]
        password = config["mqtt"].get("password", None)
        client.username_pw_set(user, password)

    # Connect to the broker.
    client.connect(config["mqtt"]["broker"], config["mqtt"]["port"])

    # Generate a random session ID to use so the server can reply directly to
    # us via MQTT.
    id = str(random.getrandbits(32))
    payload["session"] = id

    # Session topic - this must match the servers definition of the session
    # topic (i.e. don't just change it here).
    rtn_topic = "%s/session/%s" % (topic, id)
    client.message_callback_add(rtn_topic, callback)
    client.subscribe(rtn_topic)

    # Send the message).
    client.publish(topic, json.dumps(payload), qos=2)

    # Loop on the client until the callback sets the done field in the
    # session data or we time out.
    session["end_time"] = time.time() + TIME_OUT  # seconds
    while not session["done"] and time.time() < session["end_time"]:
        client.loop(timeout=0.5)

    if not session["done"]:
        print("Reply timed out")

    client.disconnect()
    return session


#===========================================================================
def callback(client, session, message):
    """MQTT message callback

    Args:
      client:   The MQTT client.
      session:  User data (the session dictionary).
      message:  The incoming message.
    """
    quiet = session["quiet"]

    # Update the end time to push the timeout time forward.
    session["end_time"] = time.time() + TIME_OUT

    # Extract the message reply object.
    msg = message.payload.decode("utf-8")
    reply = Reply.from_json(msg)

    # If the command finished, update the session tag to show that.
    if reply.type == Reply.Type.END:
        session["done"] = True

    # Print messages to the screen.
    elif reply.type == Reply.Type.MESSAGE:
        # quiet = 0 or 2: show messages
        if quiet != 1:
            print(reply.data)

    elif reply.type == Reply.Type.ERROR:
        session["status"] = -1
        if quiet != 1:
            print('ERROR:', reply.data)


#===========================================================================
