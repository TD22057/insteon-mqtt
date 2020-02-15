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
                                description="Insteon<->MQTT tool")
    p.add_argument("config", metavar="config.yaml", help="Configuration "
                   "file to use.")
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
    sp.set_defaults(func=start.start)

    #---------------------------------------
    # modem.refresh_all command
    sp = sub.add_parser("refresh-all", help="Call refresh all on the devices "
                        "in the configuration.")
    sp.add_argument("-f", "--force", action="store_true",
                    help="Force the modem/device database to be downloaded.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.set_defaults(func=modem.refresh_all)

    #---------------------------------------
    # modem.sync_all command
    sp = sub.add_parser("sync-all", help="Call sync on all the devices "
                        "in the configuration.")
    sp.add_argument("--run", action="store_true", default=False,
                    help="Perform the actions altering the device db to bring "
                    "it in sync.  If not specified, will perform a dry-run "
                    "which only lists the changes to be made.")
    sp.add_argument("--no-refresh", action="store_true", default=False,
                    help="Don't refresh the db before syncing.  This can "
                    "be dangerous if the device db is out of date.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.set_defaults(func=modem.sync_all)

    #---------------------------------------
    # modem.import_scenes_all command
    sp = sub.add_parser("import-scenes-all", help="Call import-scenes on all "
                        "the devices in the configuration.")
    sp.add_argument("--run", action="store_true", default=False,
                    help="Perform the actions altering the scenes config file "
                    "to bring it in sync.  If not specified, will perform a "
                    "dry-run which only lists the changes to be made.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.set_defaults(func=modem.import_scenes_all)

    #---------------------------------------
    # modem.factory_reset command
    sp = sub.add_parser("factory-reset", help="Perform a remote factory "
                        "reset.  Currently only supported on the modem.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.set_defaults(func=modem.factory_reset)

    #---------------------------------------
    # modem.get_devices command
    sp = sub.add_parser("get-devices", help="Return a list of all the devices "
                        "that the modem knows about.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.set_defaults(func=modem.get_devices)

    #---------------------------------------
    # device.linking command
    sp = sub.add_parser("linking", help="Turn on device or modem linking.  "
                        "This is the same as holding the modem set button "
                        "for 3 seconds.")
    sp.add_argument("-g", "--group", type=int, default=0x01,
                    help="Group number to link with (1-255)")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.linking)

    #---------------------------------------
    # device.join command
    sp = sub.add_parser("join", help="Join the device to the modem. "
                        "Allows the modem to talk to the device.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.join)

    #---------------------------------------
    # device.refresh command
    sp = sub.add_parser("refresh", help="Refresh device/modem state and "
                        "all link database.")
    sp.add_argument("-f", "--force", action="store_true",
                    help="Force the device database to be downloaded.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.refresh)

    #---------------------------------------
    # device.get_flags command
    sp = sub.add_parser("get-flags", help="Get device operating flags.")
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.get_flags)

    #---------------------------------------
    # device.set_flags command
    sp = sub.add_parser("set-flags", help="Set device operating flags.")
    sp.add_argument("address", help="Device address or name.")
    sp.add_argument("flags", nargs="+", help="FLAG=VALUE to set.  Valid "
                    "flags names are device dependent.  See the device "
                    "docs for details.")
    sp.set_defaults(func=device.set_flags)

    #---------------------------------------
    # device.get_engine command
    sp = sub.add_parser("get-engine", help="Get device engine version.")
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.get_engine)

    #---------------------------------------
    # device.get_model command
    sp = sub.add_parser("get-model", help="Get device model information.")
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.get_model)

    #---------------------------------------
    # device.on command
    sp = sub.add_parser("on", help="Turn a device on.")
    sp.add_argument("-l", "--level", metavar="level", type=int, default=255,
                    help="Level to use for dimmers (0-255)")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("-g", "--group", type=int, default=0x01,
                    help="Group (button) number to turn on for multi-button "
                    "devices.")
    sp.add_argument("-r", "--reason", metavar="reason", type=str, default="",
                    help="Reason message to send with the command.  No "
                    "message with use 'command'.")
    gp = sp.add_mutually_exclusive_group()
    gp.add_argument("-i", "--instant", dest="mode", action="store_const",
                    const="instant", help="Instant (rather than ramping) on.")
    gp.add_argument("-f", "--fast", dest="mode", action="store_const",
                    const="fast", help="Send an Insteon fast on command.")
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.on)

    #---------------------------------------
    # device.set command
    sp = sub.add_parser("set", help="Turn a device to specific level.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("-g", "--group", type=int, default=0x01,
                    help="Group (button) number to set for multi-button "
                    "devices.")
    sp.add_argument("-r", "--reason", metavar="reason", type=str, default="",
                    help="Reason message to send with the command.  No "
                    "message with use 'command'.")
    gp = sp.add_mutually_exclusive_group()
    gp.add_argument("-i", "--instant", dest="mode", action="store_const",
                    const="instant", help="Instant (rather than ramping) on.")
    gp.add_argument("-f", "--fast", dest="mode", action="store_const",
                    const="fast", help="Send an Insteon fast on command.")
    sp.add_argument("address", help="Device address or name.")
    sp.add_argument("level", type=int, default=255,
                    help="Level to use for dimmers (0-255)")
    sp.set_defaults(func=device.set)

    #---------------------------------------
    # device.off command
    sp = sub.add_parser("off", help="Turn a device off.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("-g", "--group", type=int, default=0x01,
                    help="Group (button) number to turn off for multi-button "
                    "devices.")
    sp.add_argument("-r", "--reason", metavar="reason", type=str, default="",
                    help="Reason message to send with the command.  No "
                    "message with use 'command'.")
    gp = sp.add_mutually_exclusive_group()
    gp.add_argument("-i", "--instant", dest="mode", action="store_const",
                    const="instant", help="Instant (rather than ramping) on.")
    gp.add_argument("-f", "--fast", dest="mode", action="store_const",
                    const="fast", help="Send an Insteon fast on command.")
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.off)

    #---------------------------------------
    # device.increment_up command
    sp = sub.add_parser("up", help="Increments a dimmer up.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("-r", "--reason", metavar="reason", type=str, default="",
                    help="Reason message to send with the command.  No "
                    "message with use 'command'.")
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.increment_up)

    #---------------------------------------
    # device.increment_up command
    sp = sub.add_parser("down", help="Decrements a dimmer up.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("-r", "--reason", metavar="reason", type=str, default="",
                    help="Reason message to send with the command.  No "
                    "message with use 'command'.")
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.increment_down)

    #---------------------------------------
    # device.scene command
    sp = sub.add_parser("scene", help="Simulate a scene command.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("-r", "--reason", metavar="reason", type=str, default="",
                    help="Reason message to send with the command.  No "
                    "message with use 'scene'.")
    sp.add_argument("address", help="Device address or name.")
    sp.add_argument("group", help="Group (button) number of the "
                    "scene to trigger (use 1 for single buttons.) "
                    "For modem scenes the group can alternatively be the "
                    "scene name as defined in a scenes.yaml file."
                    )
    sp.add_argument("is_on", type=int, default=1, choices=[0, 1],
                    help="1 to turn the scene on, 0 to turn it off.")
    sp.set_defaults(func=device.scene)

    #---------------------------------------
    # device.pair command
    sp = sub.add_parser("pair", help="Pair a device with the modem.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
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
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.refresh)

    #---------------------------------------
    # device.db_add add ctrl/rspdr command
    sp = sub.add_parser("db-add", help="Add the device/modem as the "
                        "controller or responder of another device.  The "
                        "addr1 input sets the device to modify.  Also adds "
                        "the corresponding entry on the linked device unless "
                        "--one-way is set.")
    sp.add_argument("-o", "--one-way", action="store_true",
                    help="Only add the entry on address1.  Otherwise the "
                    "corresponding entry on address2 is also added.")
    sp.add_argument("--no-refresh", action="store_true", default=False,
                    help="Don't refresh the db before adding.  This can "
                    "be dangerous if the device db is out of date.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("--level", type=int, help="On level (0-255) to use on "
                    "the responder (default is 0xff).")
    sp.add_argument("--ramp", type=int, help="Ramp rate (0-255) to use on "
                    "the responder (default is to use the device default).")
    sp.add_argument("--addr1-data", type=int, nargs=3, metavar="Dn",
                    help="(0-255) 3 element data list to use in addr1.  "
                    "Using wrong values can cause the link to not work (i.e. "
                    "don't use this).")
    sp.add_argument("--addr2-data", type=int, nargs=3, metavar="Dn",
                    help="(0-255) 3 element data list to use in addr2.  "
                    "Using wrong values can cause the link to not work (i.e. "
                    "don't use this).")
    sp.add_argument("addr1", help="Address of the device to update.")
    sp.add_argument("group1", type=int, help="Group (button) number on addr1.")
    sp.add_argument("mode", choices=["ctrl", "resp"],
                    help="'ctrl' for addr1 as controller of addr2.  'resp' "
                    "for addr1 as responder to addr2.")
    sp.add_argument("addr2", help="Address of the device to add to the db.")
    sp.add_argument("group2", type=int, help="Group (button) number on addr2.")
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
    sp.add_argument("--no-refresh", action="store_true", default=False,
                    help="Don't refresh the db before adding.  This can "
                    "be dangerous if the device db is out of date.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("addr1", help="Address of the device to delete.")
    sp.add_argument("mode", choices=["ctrl", "resp"],
                    help="'ctrl' for addr1 as controller of addr2.  'resp' "
                    "for addr1 as responder to addr2.")
    sp.add_argument("addr2", help="Address of the device to delete from the "
                    "db.")
    sp.add_argument("group", type=int, help="Group (button) number on the "
                    "controller (i.e. the db group number).")
    sp.set_defaults(func=device.db_delete)

    #---------------------------------------
    # device.set_button_led
    sp = sub.add_parser("set-button-led", help="Set the button LED state for "
                        "a KeyPadLinc.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("address", help="Device address or name.")
    sp.add_argument("group", type=int, help="Group (button) number to set")
    sp.add_argument("is_on", type=int, default=1, choices=[0, 1],
                    help="1 to turn the LED on, 0 to turn it off.")
    sp.set_defaults(func=device.set_button_led)

    #---------------------------------------
    # device.print_db
    sp = sub.add_parser("print-db", help="Print the current device database")
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.print_db)

    #---------------------------------------
    # device.sync
    sp = sub.add_parser("sync", help="Sync the defined scenes with device db")
    sp.add_argument("address", help="Device address or name.")
    sp.add_argument("--run", action="store_true", default=False,
                    help="Perform the actions altering the device db to bring "
                    "it in sync.  If not specified, will perform a dry-run "
                    "which only lists the changes to be made.")
    sp.add_argument("--no-refresh", action="store_true", default=False,
                    help="Don't refresh the db before syncing.  This can "
                    "be dangerous if the device db is out of date.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.set_defaults(func=device.sync)

    #---------------------------------------
    # device.import_scenes
    sp = sub.add_parser("import-scenes", help="Import all of the scenes "
                        "defined on the device into the scenes config file.")
    sp.add_argument("address", help="Device address or name.")
    sp.add_argument("--run", action="store_true", default=False,
                    help="Perform the actions altering the scenes config file "
                    " to bring it in sync.  If not specified, will perform a "
                    "dry-run which only lists the changes to be made.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.set_defaults(func=device.import_scenes)

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
