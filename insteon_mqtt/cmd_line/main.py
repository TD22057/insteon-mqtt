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
    # pylint: disable=too-many-statements
    p = argparse.ArgumentParser(prog="insteon-mqtt",
                                description="Inseton<->MQTT tool")
    sub = p.add_subparsers(help="Command help")

    #---------------------------------------
    # START command
    sp = sub.add_parser("start", help="Start the Insteon<->MQTT server.")
    sp.add_argument("config", metavar="config.yaml", help="Configuration "
                    "file to use.")
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
    sp.add_argument("config", metavar="config.yaml", help="Configuration "
                    "file to use.")
    sp.add_argument("-w", "--timeout", type=int, metavar="timeout",
                    default=30, help="Time out in seconds to end linking.")
    sp.set_defaults(func=modem.set_btn)

    #---------------------------------------
    # modem.db_delete command
    sp = sub.add_parser("db-delete", help="Delete all entries from the "
                        "modem's all link database with the input address "
                        "and group.  Also deletes the corresponding entries "
                        "on the device unless --one-way is set.")
    sp.add_argument("config", metavar="config.yaml", help="Configuration "
                    "file to use.")
    sp.add_argument("address", help="Device address of the entry to remove")
    sp.add_argument("group", type=int, help="Group number to remove (1-255)")
    sp.add_argument("-o", "--one-way", action="store_true",
                    help="Only delete the modem entries.  Otherwise the "
                    "corresponding entry on the device is also removed.")
    sp.set_defaults(func=modem.db_delete)

    #---------------------------------------
    # modem.refresh_all command
    sp = sub.add_parser("refresh-all", help="Call refresh all on the devices "
                        "in the configuration.")
    sp.add_argument("config", metavar="config.yaml", help="Configuration "
                    "file to use.")
    sp.add_argument("-f", "--force", action="store_true",
                    help="Force the modem/device database to be downloaded.")
    sp.set_defaults(func=modem.refresh_all)

    #---------------------------------------
    # device.pair command
    sp = sub.add_parser("refresh", help="Refresh device/modem state and "
                        "all link database.")
    sp.add_argument("config", metavar="config.yaml", help="Configuration "
                    "file to use.")
    sp.add_argument("address", help="Device address or name.")
    sp.add_argument("-f", "--force", action="store_true",
                    help="Force the device database to be downloaded.")
    sp.set_defaults(func=device.refresh)

    #---------------------------------------
    # device.on command
    sp = sub.add_parser("on", help="Turn a device on.")
    sp.add_argument("config", metavar="config.yaml", help="Configuration "
                    "file to use.")
    sp.add_argument("address", help="Device address or name.")
    sp.add_argument("-l", "--level", metavar="level", type=int, default=255,
                    help="Level to use for dimmers (0-255)")
    sp.add_argument("-i", "--instant", action="store_true",
                    help="Instant (rather than ramping) on.")
    sp.set_defaults(func=device.on)

    #---------------------------------------
    # device.set command
    sp = sub.add_parser("set", help="Turn a device to specific level.")
    sp.add_argument("config", metavar="config.yaml", help="Configuration "
                    "file to use.")
    sp.add_argument("address", help="Device address or name.")
    sp.add_argument("level", type=int, default=255,
                    help="Level to use for dimmers (0-255)")
    sp.add_argument("-i", "--instant", action="store_true",
                    help="Instant (rather than ramping) on.")
    sp.set_defaults(func=device.on)  # on takes the same args to use that

    #---------------------------------------
    # device.off command
    sp = sub.add_parser("off", help="Turn a device off.")
    sp.add_argument("config", metavar="config.yaml", help="Configuration "
                    "file to use.")
    sp.add_argument("address", help="Device address or name.")
    sp.add_argument("-i", "--instant", action="store_true",
                    help="Instant (rather than ramping) on.")
    sp.set_defaults(func=device.off)

    #---------------------------------------
    # device.increment_up command
    sp = sub.add_parser("up", help="Increments a dimmer up.")
    sp.add_argument("config", metavar="config.yaml", help="Configuration "
                    "file to use.")
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.increment_up)

    #---------------------------------------
    # device.increment_up command
    sp = sub.add_parser("down", help="Decrements a dimmer up.")
    sp.add_argument("config", metavar="config.yaml", help="Configuration "
                    "file to use.")
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.increment_down)

    #---------------------------------------
    # device.pair command
    sp = sub.add_parser("pair", help="Pair a device with the modem.")
    sp.add_argument("config", metavar="config.yaml", help="Configuration "
                    "file to use.")
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.pair)

    #---------------------------------------
    # device.pair command
    sp = sub.add_parser("refresh", help="Refresh device/modem state and "
                        "all link database.")
    sp.add_argument("config", metavar="config.yaml", help="Configuration "
                    "file to use.")
    sp.add_argument("address", help="Device address or name.")
    sp.add_argument("-f", "--force", action="store_true",
                    help="Force the device database to be downloaded.")
    sp.set_defaults(func=device.refresh)

    #---------------------------------------
    # device.db_add_ctrl_of command
    sp = sub.add_parser("db-add", help="Add the device/modem as the "
                        "controller of another device.  Also adds the "
                        "corresponding entry on the linked device unless "
                        "--one-way is set.")
    sp.add_argument("config", metavar="config.yaml", help="Configuration "
                    "file to use.")
    sp.add_argument("link", help="'address1 -> address2' to update address1 "
                    "as a controller of address2.  'address1 <- address2' to "
                    "update address1 as a responder of address2.")
    sp.add_argument("group", type=int, help="Group number to add (1-255)")
    sp.add_argument("-o", "--one-way", action="store_true",
                    help="Only add the entry on address1.  Otherwise the "
                    "corresponding entry on address2 is also added.")
    sp.set_defaults(func=device.db_add)

    # TODO: add support for device.db_del_ctrl_of and db_del_resp_of.
    # The problem is the modem can't handle those commands.  Best way
    # to fix this is to re-code Modem.db_delete to be smart and delete
    # all the entries and then re-add the ones that weren't the input
    # command.  That way from the outside the modem and devices have
    # the same API.

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
