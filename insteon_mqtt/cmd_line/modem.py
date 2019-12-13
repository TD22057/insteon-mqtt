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
def sync_all(args, config):
    topic = "%s/modem" % (args.topic)
    payload = {
        "cmd" : "sync_all",
        "refresh" : not args.no_refresh,
        "dry_run" : not args.run
        }

    reply = util.send(config, topic, payload, args.quiet)
    return reply["status"]


#===========================================================================
def import_scenes_all(args, config):
    topic = "%s/modem" % (args.topic)
    payload = {
        "cmd" : "import_scenes_all",
        "dry_run" : not args.run
        }

    reply = util.send(config, topic, payload, args.quiet)
    return reply["status"]


#===========================================================================
def factory_reset(args, config):
    topic = "%s/modem" % (args.topic)
    payload = {
        "cmd" : "factory_reset",
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
