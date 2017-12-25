#===========================================================================
#
# Command line parsing and main entry point.
#
#===========================================================================
import argparse
import sys
from .. import config
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
    sp.add_argument("-l", "--log", metavar="log_file",
                    help="Logging file to use.")
    sp.add_argument("-ls", "--log-screen", action="store_true",
                    help="Log to the screen")
    sp.add_argument("--level", metavar="log_level", type=int,
                    help="Logging level to use.  10=debug, 20=info,"
                    "30=warn, 40=error, 50=critical")
    sp.add_argument("config", metavar="config.yaml", help="Configuration "
                    "file to use.")
    sp.set_defaults(func=start.start)

    #---------------------------------------
    # modem.refresh_all command
    sp = sub.add_parser("refresh-all", help="Call refresh all on the devices "
                        "in the configuration.")
    sp.add_argument("-f", "--force", action="store_true",
                    help="Force the modem/device database to be downloaded.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("config", metavar="config.yaml", help="Configuration "
                    "file to use.")
    sp.set_defaults(func=modem.refresh_all)

    #---------------------------------------
    # device.linking command
    sp = sub.add_parser("linking", help="Turn on device or modem linking.  "
                        "This is the same as holding the modem set button "
                        "for 3 seconds.")
    sp.add_argument("-g", "--group", type=int, default=0x01,
                    help="Group number to link with (1-255)")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("config", metavar="config.yaml", help="Configuration "
                    "file to use.")
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.linking)

    #---------------------------------------
    # device.refresh command
    sp = sub.add_parser("refresh", help="Refresh device/modem state and "
                        "all link database.")
    sp.add_argument("-f", "--force", action="store_true",
                    help="Force the device database to be downloaded.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("config", metavar="config.yaml", help="Configuration "
                    "file to use.")
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.refresh)

    #---------------------------------------
    # device.on command
    sp = sub.add_parser("on", help="Turn a device on.")
    sp.add_argument("-l", "--level", metavar="level", type=int, default=255,
                    help="Level to use for dimmers (0-255)")
    sp.add_argument("-i", "--instant", action="store_true",
                    help="Instant (rather than ramping) on.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("config", metavar="config.yaml", help="Configuration "
                    "file to use.")
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.on)

    #---------------------------------------
    # device.set command
    sp = sub.add_parser("set", help="Turn a device to specific level.")
    sp.add_argument("-i", "--instant", action="store_true",
                    help="Instant (rather than ramping) on.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("config", metavar="config.yaml", help="Configuration "
                    "file to use.")
    sp.add_argument("address", help="Device address or name.")
    sp.add_argument("level", type=int, default=255,
                    help="Level to use for dimmers (0-255)")
    sp.set_defaults(func=device.set)

    #---------------------------------------
    # device.off command
    sp = sub.add_parser("off", help="Turn a device off.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("-i", "--instant", action="store_true",
                    help="Instant (rather than ramping) on.")
    sp.add_argument("config", metavar="config.yaml", help="Configuration "
                    "file to use.")
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.off)

    #---------------------------------------
    # device.increment_up command
    sp = sub.add_parser("up", help="Increments a dimmer up.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("config", metavar="config.yaml", help="Configuration "
                    "file to use.")
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.increment_up)

    #---------------------------------------
    # device.increment_up command
    sp = sub.add_parser("down", help="Decrements a dimmer up.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("config", metavar="config.yaml", help="Configuration "
                    "file to use.")
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.increment_down)

    #---------------------------------------
    # device.pair command
    sp = sub.add_parser("pair", help="Pair a device with the modem.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("config", metavar="config.yaml", help="Configuration "
                    "file to use.")
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.pair)

    #---------------------------------------
    # device.pair command
    sp = sub.add_parser("refresh", help="Refresh device/modem state and "
                        "all link database.")
    sp.add_argument("-f", "--force", action="store_true",
                    help="Force the device database to be downloaded.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("config", metavar="config.yaml", help="Configuration "
                    "file to use.")
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.refresh)

    #---------------------------------------
    # device.db_add add ctrl/rspdr command
    sp = sub.add_parser("db-add", help="Add the device/modem as the "
                        "controller of another device.  Also adds the "
                        "corresponding entry on the linked device unless "
                        "--one-way is set.")
    sp.add_argument("-o", "--one-way", action="store_true",
                    help="Only add the entry on address1.  Otherwise the "
                    "corresponding entry on address2 is also added.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("config", metavar="config.yaml", help="Configuration "
                    "file to use.")
    sp.add_argument("link", help="'address1 -> address2' to update address1 "
                    "as a controller of address2.  'address1 <- address2' to "
                    "update address1 as a responder of address2.")
    sp.add_argument("group", type=int, help="Group number to add (1-255)")
    sp.add_argument("data", nargs="*",
                    help="3 data element to set in the link database.  Each "
                    "must be in the range 0->255.  May be hex with a '0x' "
                    "prefix (0x10) or an integer input.  Default is [0,0,0].")
    sp.set_defaults(func=device.db_add)

    #---------------------------------------
    # device.db_del delete ctrl/rspdr command
    sp = sub.add_parser("db-delete", help="Delete an entry in the device/"
                        "modem's all link database with the input address, "
                        "group, and mode.  Also deletes the corresponding "
                        "entry on the linked device unless --one-way is set.")
    sp.add_argument("-o", "--one-way", action="store_true",
                    help="Only delete the modem entries.  Otherwise the "
                    "corresponding entry on the device is also removed.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("config", metavar="config.yaml", help="Configuration "
                    "file to use.")
    sp.add_argument("device", help="Modem/Device address or name of the "
                    "database to modify")
    sp.add_argument("address", help="Modem/Device address or name of the "
                    "entry to remove")
    sp.add_argument("group", type=int, help="Group number to remove (1-255)")
    sp.add_argument("mode", choices=["CTRL", "RESP"],
                    help="Controller or responder flag of the entry to remove")
    sp.set_defaults(func=device.db_delete)

    #---------------------------------------
    # device.set_button_led
    sp = sub.add_parser("set-button-led", help="Set the button LED state for "
                        "a KeyPadLinc.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("config", metavar="config.yaml", help="Configuration "
                    "file to use.")
    sp.add_argument("address", help="Device address or name.")
    sp.add_argument("button", type=int, help="Button (group) number to set")
    sp.add_argument("is_on", type=int, default=1, choices=[0,1],
                    help="1 to turn the LED on, 0 to turn it off.")
    sp.set_defaults(func=device.set_button_led)

    return p.parse_args(args)


#===========================================================================
def main(mqtt_converter=None):
    args = parse_args(sys.argv[1:])

    # Load the configuration file.
    cfg = config.load(args.config)

    topic = cfg.get("mqtt", {}).get("cmd_topic", None)
    if topic:
        args.topic = topic

    return args.func(args, cfg)

#===========================================================================
