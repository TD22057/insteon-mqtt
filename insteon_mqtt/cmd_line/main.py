#===========================================================================
#
# Command line parsing and main entry point.
#
#===========================================================================
import argparse
import sys
import yaml
from . import device
from . import modem
from . import start


def parse_args(args):
    """Input is command line arguments w/o arg[0]
    """
    p = argparse.ArgumentParser(prog="insteon-mqtt",
                                description="Inseton<->MQTT tool")
    p.add_argument("config", metavar="config.yaml", help="Config file to use.")
    sub = p.add_subparsers()

    #---------------------------------------
    # START command
    sp = sub.add_parser("start", help="Start the Insteon<->MQTT server.")
    sp.add_argument("-l", "--log", metavar="log_File",
                   help="Logging file to use.  Use 'stdout' for the screen.")
    sp.add_argument("--level", metavar="log_level", type=int,
                   help="Logging level to use.  10=debug, 20=info,"
                   "30=warn, 40=error, 50=critical")
    sp.set_defaults(func=start.start)

    #---------------------------------------
    # modem.set command
    sp = sub.add_parser("link", help="Turn on modem linking.  This is the "
                        "same as pressing the modem set button.")
    sp.add_argument("-w", "--timeout", type=int, metavar="timeout",
                    default=30, help="Time out in seconds to end linking.")
    sp.set_defaults(func=modem.set_btn)

    #---------------------------------------
    # device.on command
    sp = sub.add_parser("on", help="Turn a device on.")
    sp.add_argument("address", help="Device address or name.")
    sp.add_argument("-l", "--level", metavar="level", type=int, default=255,
                    help="Level to use for dimmers (0-255)")
    sp.add_argument("-i", "--instant", action="store_true",
                    help="Instant (rather than ramping) on.")
    sp.set_defaults(func=device.on)

    #---------------------------------------
    # device.set command
    sp = sub.add_parser("set", help="Turn a device to specific level.")
    sp.add_argument("address", help="Device address or name.")
    sp.add_argument("level", type=int, default=255,
                    help="Level to use for dimmers (0-255)")
    sp.add_argument("-i", "--instant", action="store_true",
                    help="Instant (rather than ramping) on.")
    sp.set_defaults(func=device.on)  # on takes the same args to use that

    #---------------------------------------
    # device.off command
    sp = sub.add_parser("off", help="Turn a device off.")
    sp.add_argument("address", help="Device address or name.")
    sp.add_argument("-i", "--instant", action="store_true",
                    help="Instant (rather than ramping) on.")
    sp.set_defaults(func=device.off)

    s = """
    ALL:
    'db_add_ctrl_of': addr, group, [data], [two_way]
    'db_add_resp_of': addr, group, [data], [two_way]
    'db_get'
    'refresh'

    MODEM:
    'db_delete': addr, group, [two_way]
    'reload_all'

    DEVICE:
    'db_del_ctrl_of': addr, group, [two_way]
    'db_del_resp_of': addr, group, [two_way]
    'pair'

    DIMMER:
    'increment_up'
    'increment_down'
    """

    #---------------------------------------
    # modem.add_ctrl command
    s = """
    sp = sub.add_parser("addctrl", help="Turn on modem linking.")
    sp.set_defaults(func=add.add_ctrl)
    sp.add_argument("address", help="Device address or name or 'modem'.")
    sp.add_argument("group", type=int, help="Group number to use (1-255)")
    sp.add_argument("-o", "--one-way", action="set_true",
                    help="Only link one way - otherwise a responder link is "
                    "also created on the other device.")
    sp.add_argument("-d", "--data", metavar="data",
                    help="3 comma separated integers (each 0-255) to send as "
                    "the data element. e.g. 1,2,3 or 0,0,1 (no spaces)")

    #---------------------------------------
    # db_get command
    sp = sub.add_parser("db_get", help="Download db from a device.")
    sp.set_defaults(func=db.get)
    sp.add_argument("address", help="Device address or name.")

    #---------------------------------------
    # refresh command
    sp = sub.add_parser("refresh", help="Check if the db is current.")
    sp.set_defaults(func=db.refresh)
    sp.add_argument("address", help="Device address or name.")
    """
    return p.parse_args(args)


#===========================================================================
def main(mqtt_converter=None):
    args = parse_args(sys.argv[1:])

    # Load the configuration file.
    with open(args.config) as f:
        config = yaml.load(f.read())

    topic = config.get("mqtt", {}).get("cmd_topic", None)
    if topic:
        args.topic = topic

    args.func(args, config)

#===========================================================================
