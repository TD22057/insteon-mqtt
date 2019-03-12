#===========================================================================
#
# Device commands
#
#===========================================================================
from . import util


#===========================================================================
def linking(args, config):
    topic = "%s/%s" % (args.topic, args.address)
    payload = {
        "cmd" : "linking",
        "group" : args.group,
        }

    reply = util.send(config, topic, payload, args.quiet)
    return reply["status"]


#===========================================================================
def join(args, config):
    topic = "%s/%s" % (args.topic, args.address)
    payload = {
        "cmd" : "join",
        }

    reply = util.send(config, topic, payload, args.quiet)
    return reply["status"]


#===========================================================================
def set_button_led(args, config):
    topic = "%s/%s" % (args.topic, args.address)
    payload = {
        "cmd" : "set_button_led",
        "group" : args.group,
        "is_on" : bool(args.is_on),
        }

    reply = util.send(config, topic, payload, args.quiet)
    return reply["status"]


#===========================================================================
def get_flags(args, config):
    topic = "%s/%s" % (args.topic, args.address)
    payload = {
        "cmd" : "get_flags",
        }

    reply = util.send(config, topic, payload, False)
    return reply["status"]


#===========================================================================
def set_flags(args, config):
    topic = "%s/%s" % (args.topic, args.address)
    payload = {
        "cmd" : "set_flags",
        }

    for flag in args.flags:
        elem = flag.split("=")
        assert len(elem) == 2

        key = elem[0].strip().lower()
        value = elem[1].strip()
        payload[key] = value

    reply = util.send(config, topic, payload, False)
    return reply["status"]


#===========================================================================
def get_engine(args, config):
    topic = "%s/%s" % (args.topic, args.address)
    payload = {
        "cmd" : "get_engine",
        }

    reply = util.send(config, topic, payload, False)
    return reply["status"]


#===========================================================================
def get_model(args, config):
    topic = "%s/%s" % (args.topic, args.address)
    payload = {
        "cmd" : "get_model",
        }

    reply = util.send(config, topic, payload, False)
    return reply["status"]


#===========================================================================
def print_db(args, config):
    topic = "%s/%s" % (args.topic, args.address)
    payload = {
        "cmd" : "print_db",
        }

    reply = util.send(config, topic, payload, False)
    return reply["status"]


#===========================================================================
def on(args, config):
    topic = "%s/%s" % (args.topic, args.address)
    payload = {
        "cmd" : "on",
        "level" : args.level,
        "group" : args.group,
        }
    if args.mode:
        payload["mode"] = args.mode

    reply = util.send(config, topic, payload, args.quiet)
    return reply["status"]


#===========================================================================
def off(args, config):
    topic = "%s/%s" % (args.topic, args.address)
    payload = {
        "cmd" : "off",
        "group" : args.group,
        }
    if args.mode:
        payload["mode"] = args.mode

    reply = util.send(config, topic, payload, args.quiet)
    return reply["status"]


#===========================================================================
def set(args, config):
    topic = "%s/%s" % (args.topic, args.address)
    payload = {
        "cmd" : "set",
        "level" : args.level,
        "group" : args.group,
        }
    if args.mode:
        payload["mode"] = args.mode

    reply = util.send(config, topic, payload, args.quiet)
    return reply["status"]


#===========================================================================
def increment_up(args, config):
    topic = "%s/%s" % (args.topic, args.address)
    payload = {
        "cmd" : "increment_up",
        }

    reply = util.send(config, topic, payload, args.quiet)
    return reply["status"]


#===========================================================================
def increment_down(args, config):
    topic = "%s/%s" % (args.topic, args.address)
    payload = {
        "cmd" : "increment_down",
        }

    reply = util.send(config, topic, payload, args.quiet)
    return reply["status"]


#===========================================================================
def scene(args, config):
    topic = "%s/%s" % (args.topic, args.address)
    payload = {
        "cmd" : "scene",
        "group" : args.group,
        "is_on" : bool(args.is_on),
        }

    reply = util.send(config, topic, payload, args.quiet)
    return reply["status"]


#===========================================================================
def pair(args, config):
    topic = "%s/%s" % (args.topic, args.address)
    payload = {
        "cmd" : "pair",
        }

    reply = util.send(config, topic, payload, args.quiet)

    if reply["status"]:
        print("Pairing may fail if the modem db is out of date.  Try running")
        print("the following and then re-try the pair command.")
        print("   insteont-mqtt config.py refresh modem")

    return reply["status"]


#===========================================================================
def refresh(args, config):
    topic = "%s/%s" % (args.topic, args.address)
    payload = {
        "cmd" : "refresh",
        "force" : args.force,
        }

    reply = util.send(config, topic, payload, args.quiet)
    return reply["status"]


#===========================================================================
def db_add(args, config):
    # Resolve the data elements to set for each item.  Defaults are None or
    # -1 for each element.

    # The controller data is either None or the full input args.
    if args.mode == "ctrl":
        cmd = "db_add_ctrl_of"
        addr1_data = args.addr1_data
    else:
        cmd = "db_add_resp_of"
        addr2_data = args.addr2_data

    if args.mode == "ctrl":
        resp_data = args.addr2_data
    else:
        resp_data = args.addr1_data

    # Responder data may contains the level and ramp rates.
    if args.level is not None or args.ramp is not None:
        if resp_data is None:
            resp_data = [-1, -1, -1]
            if args.level is not None:
                resp_data[0] = args.level
            if args.ramp is not None:
                resp_data[1] = args.ramp

    if args.mode == "ctrl":
        addr2_data = resp_data
    else:
        addr1_data = resp_data

    topic = "%s/%s" % (args.topic, args.addr1)
    payload = {
        "cmd" : cmd,
        "local_group" : args.group1,
        "remote_addr" : args.addr2,
        "remote_group" : args.group2,
        "two_way" : not args.one_way,
        "refresh" : not args.no_refresh,
        "local_data" : addr1_data,
        "remote_data" : addr2_data,
        }

    reply = util.send(config, topic, payload, args.quiet)
    return reply["status"]


#===========================================================================
def db_delete(args, config):
    if args.mode == "ctrl":
        cmd = "db_del_ctrl_of"
    else:
        cmd = "db_del_resp_of"

    topic = "%s/%s" % (args.topic, args.addr1)
    payload = {
        "cmd" : cmd,
        "addr" : args.addr2,
        "group" : args.group,
        "two_way" : not args.one_way,
        "refresh" : not args.no_refresh,
        }

    reply = util.send(config, topic, payload, args.quiet)
    return reply["status"]


#===========================================================================
