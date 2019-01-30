#===========================================================================
#
# Modem only commands
#
#===========================================================================
from . import util


#===========================================================================
def refresh_all(args, config):
    topic = "%s/modem" % (args.topic)
    payload = {
        "cmd" : "refresh_all",
        "force" : args.force,
        }

    reply = util.send(config, topic, payload, args.quiet)
    return reply["status"]


#===========================================================================
def get_devices(args, config):
    topic = "%s/modem" % (args.topic)
    payload = {
        "cmd" : "get_devices",
        }

    reply = util.send(config, topic, payload, args.quiet)
    return reply["status"]


#===========================================================================
