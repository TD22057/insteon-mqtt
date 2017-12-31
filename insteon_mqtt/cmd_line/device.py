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
    return reply["result"]


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
def on(args, config):
    topic = "%s/%s" % (args.topic, args.address)
    payload = {
        "cmd" : "on",
        "level" : args.level,
        "instant" : args.instant,
        "group" : args.group,
        }

    reply = util.send(config, topic, payload, args.quiet)
    return reply["status"]


#===========================================================================
def off(args, config):
    topic = "%s/%s" % (args.topic, args.address)
    payload = {
        "cmd" : "off",
        "instant" : args.instant,
        "group" : args.group,
        }

    reply = util.send(config, topic, payload, args.quiet)
    return reply["status"]


#===========================================================================
def set(args, config):
    topic = "%s/%s" % (args.topic, args.address)
    payload = {
        "cmd" : "set",
        "level" : args.level,
        "instant" : args.instant,
        "group" : args.group,
        }

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
    addr1, addr2, mode = util.parse_link(args.link)
    if mode == "CTRL":
        cmd = "db_add_ctrl_of"
    else:
        cmd = "db_add_resp_of"

    # Use strings for the default - the parser below converts to int.
    data = None
    if args.data:
        if len(args.data) > 3:
            raise ValueError("Input data field %s should be 0-3 integer "
                             "values." % args.data)

        # Pad the data inputs out to 3 elements and convert any strings to
        # integers.
        data = []
        for i in range(3):
            value = 0
            if i < len(args.data):
                if "0x" in args.data[i]:
                    value = int(args.data[i], 16)
                else:
                    value = int(args.data[i])

            data.append(value)

    topic = "%s/%s" % (args.topic, addr1)
    payload = {
        "cmd" : cmd,
        "addr" : addr2,
        "group" : args.group,
        "two_way" : not args.one_way,
        "data" : data,
        "refresh" : not args.no_refresh,
        }

    reply = util.send(config, topic, payload, args.quiet)
    return reply["status"]


#===========================================================================
def db_delete(args, config):
    addr1, addr2, mode = util.parse_link(args.link)
    if mode == "CTRL":
        cmd = "db_del_ctrl_of"
    else:
        cmd = "db_del_resp_of"

    topic = "%s/%s" % (args.topic, addr1)
    payload = {
        "cmd" : cmd,
        "addr" : addr2,
        "group" : args.group,
        "two_way" : not args.one_way,
        "refresh" : not args.no_refresh,
        }

    reply = util.send(config, topic, payload, args.quiet)
    return reply["status"]


#===========================================================================
