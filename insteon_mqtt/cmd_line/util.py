#===========================================================================
#
# Command line utilities
#
#===========================================================================
import ssl
import json
import random
import time
import paho.mqtt.client as mqtt
from ..mqtt import Reply

# Time between messages before we decide that the something went wrong and
# stop.  Currently the server should send enough messages to avoid this but
# there is no pure right answer for what this should be.
TIME_OUT = 30

# map for Paho acceptable TLS cert request options
CERT_REQ_OPTIONS = {'none': ssl.CERT_NONE, 'required': ssl.CERT_REQUIRED}

# Map for Paho acceptable TLS version options. Some options are
# dependent on the OpenSSL install so catch exceptions
TLS_VER_OPTIONS = dict()
try:
    TLS_VER_OPTIONS['tls'] = ssl.PROTOCOL_TLS
except AttributeError:
    pass
try:
    TLS_VER_OPTIONS['tlsv1'] = ssl.PROTOCOL_TLSv1
except AttributeError:
    pass
try:
    TLS_VER_OPTIONS['tlsv11'] = ssl.PROTOCOL_TLSv1_1
except AttributeError:
    pass
try:
    TLS_VER_OPTIONS['tlsv12'] = ssl.PROTOCOL_TLSv1_2
except AttributeError:
    pass
try:
    TLS_VER_OPTIONS['sslv2'] = ssl.PROTOCOL_SSLv2
except AttributeError:
    pass
try:
    TLS_VER_OPTIONS['sslv23'] = ssl.PROTOCOL_SSLv23
except AttributeError:
    pass
try:
    TLS_VER_OPTIONS['sslv3'] = ssl.PROTOCOL_SSLv3
except AttributeError:
    pass

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

    encryption = config["mqtt"].get('encryption', {})
    if encryption is None:
        encryption = {}
    ca_cert = encryption.get('ca_cert', None)
    if ca_cert is not None and ca_cert != "":
        # Set the basic arguments
        certfile = encryption.get('certfile', None)
        if certfile == "":
            certfile = None
        keyfile = encryption.get('keyfile', None)
        if keyfile == "":
            keyfile = None
        ciphers = encryption.get('ciphers', None)
        if ciphers == "":
            ciphers = None

        # These require passing specific constants so we use a lookup
        # map for them.
        addl_tls_kwargs = {}
        tls_ver = encryption.get('tls_version', 'tls')
        tls_version_const = TLS_VER_OPTIONS.get(tls_ver, None)
        if tls_version_const is not None:
            addl_tls_kwargs['tls_version'] = tls_version_const
        cert_reqs = encryption.get('cert_reqs', None)
        cert_reqs = CERT_REQ_OPTIONS.get(cert_reqs, None)
        if cert_reqs is not None:
            addl_tls_kwargs['cert_reqs'] = cert_reqs

        # Finally, try the connection
        try:
            client.tls_set(ca_certs=ca_cert,
                           certfile=certfile,
                           keyfile=keyfile,
                           ciphers=ciphers, **addl_tls_kwargs)
        except FileNotFoundError as e:
            print("Cannot locate a SSL/TLS file = %s.", e)

        except ssl.SSLError as e:
            print("SSL/TLS Config error = %s.", e)

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
        print("Command line timed out waiting for a reply, the command may " +
              "still be running.")

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
