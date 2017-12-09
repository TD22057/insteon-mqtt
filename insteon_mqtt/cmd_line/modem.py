#===========================================================================
#
# Modem commands
#
#===========================================================================
from . import util


#===========================================================================
def set_btn(args, config):
    topic = "%s/modem" % (args.topic)
    payload = {
        "cmd" : "set_btn",
        "time_out" : args.timeout,
        }

    reply = util.send(config, topic, payload)
    return reply["result"]


#===========================================================================
def refresh_all(args, config):
    topic = "%s/modem" % (args.topic)
    payload = {
        "cmd" : "refresh_all",
        "force" : args.force,
        }

    reply = util.send(config, topic, payload)
    return reply["result"]


#===========================================================================
def db_delete(args, config):
    topic = "%s/modem" % (args.topic)
    payload = {
        "cmd" : "db_delete",
        "addr" : config.address,
        "group" : config.group,
        "two_way" : not args.one_way,
        }

    reply = util.send(config, topic, payload)
    return reply["result"]


#===========================================================================
