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
def on(args, config):
    topic = "%s/%s" % (args.topic, args.address)
    payload = {
        "cmd" : "on",
        "level" : args.level,
        "instant" : args.instant,
        }

    reply = util.send(config, topic, payload, args.quiet)
    return reply["status"]


#===========================================================================
def off(args, config):
    topic = "%s/%s" % (args.topic, args.address)
    payload = {
        "cmd" : "off",
        "instant" : args.instant,
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
    elem1 = args.link.split("->")
    elem2 = args.link.split("<-")

    if len(elem1) == 2:
        address1 = elem1[0].strip()
        address2 = elem1[1].strip()
        cmd = "db_add_ctrl_of"

    elif len(elem2) == 2:
        address1 = elem2[0].strip()
        address2 = elem2[1].strip()
        cmd = "db_add_resp_of"

    else:
        raise ValueError("Input link '%s' should be 'addr1 <- addr2' or "
                         "'addr1 -> addr2'." % args.link)

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

    topic = "%s/%s" % (args.topic, address1)
    payload = {
        "cmd" : cmd,
        "addr" : address2,
        "group" : args.group,
        "two_way" : not args.one_way,
        "data" : data,
        }

    reply = util.send(config, topic, payload, args.quiet)
    return reply["status"]


#===========================================================================
def db_delete(args, config):
    if args.mode == "CTRL":
        cmd = "db_del_ctrl_of"
    else:
        cmd = "db_del_resp_of"

    topic = "%s/%s" % (args.topic, args.device)
    payload = {
        "cmd" : cmd,
        "addr" : args.address,
        "group" : args.group,
        "two_way" : not args.one_way,
        }

    reply = util.send(config, topic, payload, args.quiet)
    return reply["status"]


#===========================================================================
