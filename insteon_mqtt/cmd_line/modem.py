#===========================================================================
#
# Modem commands
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
    return reply["result"]


#===========================================================================
