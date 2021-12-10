#===========================================================================
#
# Command line parsing and main entry point.
#
#===========================================================================
import sys
from . import argparse_ext
from .. import config
from . import device
from . import modem
from . import start
from ..const import __version__


def parse_args(args):
    """Input is command line arguments w/o arg[0]
    """
    # pylint: disable=too-many-statements
    prog_description = """ This is a Python 3 package that communicates with
                       an Insteon PLM modem (USB and serial) or an Insteon Hub
                       and converts Insteon state changes to MQTT and MQTT
                       commands to Insteon commands. It allows an Insteon
                       network to be integrated into and controlled from
                       anything that can use MQTT. This package works well
                       with HomeAssistant and can be easily installed as an
                       addon using the HomeAssistant Supervisor."""
    p = argparse_ext.ArgumentParser(prog="insteon-mqtt",
                                    description=prog_description)
    p.add_argument('-v', '--version', action='version', version='%(prog)s ' +
                   __version__)
    p.add_argument("config", metavar="config.yaml", help="Configuration "
                   "file to use.")
    sub = p.add_subparsers(title="commands",
                           description="See %(prog)s config.yaml <command> -h"
                                       " for specific command help.",
                           metavar="command")

    # Define sub-parser groups.  The order they appear here will define the
    # order they print on the screen
    startgrp = sub.add_parser_group('\n    Startup:')
    initgrp = sub.add_parser_group('\n    Initialize:')
    commandgrp = sub.add_parser_group('\n    Device Commands:')
    infogrp = sub.add_parser_group('\n    Get Information:')
    configgrp = sub.add_parser_group('\n    Configure:')
    linkgrp = sub.add_parser_group('\n    Link Management:')
    systemgrp = sub.add_parser_group('\n    System Wide:')
    batterygrp = sub.add_parser_group('\n    Battery Devices:')
    advancedgrp = sub.add_parser_group('\n    Advanced Commands:')

    # Define sub-parser commands.  The order they appear here will define the
    # order they appear within their respective groups.

    #---------------------------------------
    # START command
    sp = startgrp.add_parser("start", help="Start the Insteon<->MQTT server.",
                             description="Start the Insteon<->MQTT server.")
    sp.add_argument("-l", "--log", metavar="log_file",
                    help="Logging file to use.")
    sp.add_argument("-ls", "--log-screen", action="store_true",
                    help="Log to the screen")
    sp.add_argument("--level", metavar="log_level", type=int,
                    help="Logging level to use.  10=debug, 20=info,"
                    "30=warn, 40=error, 50=critical")
    sp.set_defaults(func=start.start)

    #---------------------------------------
    # modem.join_all command
    sp = systemgrp.add_parser("join-all", help="Run 'join' command on all "
                              "devices.",
                              description="Run 'join' command on all devices.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.set_defaults(func=modem.join_all)

    #---------------------------------------
    # modem.pair_all command
    sp = systemgrp.add_parser("pair-all", help="Run 'pair' command on all "
                              "devices.",
                              description="Run 'pair' command on all devices.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.set_defaults(func=modem.pair_all)

    #---------------------------------------
    # modem.refresh_all command
    sp = systemgrp.add_parser("refresh-all", help="Run 'refresh' command on "
                              "all devices.",
                              description="Run 'refresh' command on all "
                              "devices.")
    sp.add_argument("-f", "--force", action="store_true",
                    help="Force the modem/device database to be downloaded.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.set_defaults(func=modem.refresh_all)

    # modem.get_engine_all command
    sp = systemgrp.add_parser("get-engine-all", help="Run 'get-engine' "
                              "command on all devices.",
                              description="Run 'get-engine' command on all "
                              "devices.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.set_defaults(func=modem.get_engine_all)

    #---------------------------------------
    # modem.sync_all command
    sp = systemgrp.add_parser("sync-all", help="Run 'sync' command on all "
                              "devices.",
                              description="Run 'sync' command on all devices. "
                              "This will add or remove links on the device to "
                              "match those defined in the scenes.yaml file.")
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
    sp = systemgrp.add_parser("import-scenes-all", help="Run 'import-scenes' "
                              "command on all devices.",
                              description="Run 'import-scenes' command on all "
                              "devices. This will add all links defined on "
                              "the devices to the scenes.yaml file.  Any link "
                              "defined in the scenes.yaml file that is not "
                              "present on the devices will be DELETED.")
    sp.add_argument("--run", action="store_true", default=False,
                    help="Perform the actions altering the scenes config file "
                    "to bring it in sync.  If not specified, will perform a "
                    "dry-run which only lists the changes to be made.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.set_defaults(func=modem.import_scenes_all)

    #---------------------------------------
    # modem.get_devices command
    sp = infogrp.add_parser("get-devices", help="Print a list of all the "
                            "devices that the program knows about.",
                            description="Print a list of all the devices "
                                        "that the program knows about.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.set_defaults(func=modem.get_devices)

    #---------------------------------------
    # device.print_db
    sp = linkgrp.add_parser("print-db", help="Print the cache of the device "
                            "database.",
                            description="Print the cache of the device "
                            "database.")
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.print_db)

    #---------------------------------------
    # device.refresh command
    sp = linkgrp.add_parser("refresh", help="Refresh device state and link "
                            "database.",
                            description="Refresh device state and link "
                            "database.")
    sp.add_argument("-f", "--force", action="store_true",
                    help="Force the device database to be downloaded.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.refresh)

    #---------------------------------------
    # device.linking command
    sp = linkgrp.add_parser("linking", help="Put device into linking mode.",
                            description="Put device into linking mode. This "
                                        "is the same as holding the device "
                                        "set button for 3 seconds.")
    sp.add_argument("-g", "--group", type=int, default=0x01,
                    help="Group number to link with (1-255)")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.linking)

    #---------------------------------------
    # device.join command
    sp = initgrp.add_parser("join", help="Join a device to the modem.",
                            description="Join a device to the modem. "
                            "This adds a modem->device link, which "
                            "allows the modem to talk to the device. "
                            "This is generally the first thing you need "
                            "to do with a new device.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.join)

    #---------------------------------------
    # device.get_flags command
    sp = infogrp.add_parser("get-flags", help="Get device operating flags.",
                            description="Get the device operating flags.")
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.get_flags)

    #---------------------------------------
    # device.set_flags command
    sp = configgrp.add_parser("set-flags", help="Set device operating flags.",
                              description="Set device operating flags. "
                              "Flags are set using FLAG=VALUE format. "
                              "Use an intentionally bad flag such as "
                              "BAD=FLAG to see a list of valid flags.")
    sp.add_argument("address", help="Device address or name.")
    sp.add_argument("flags", nargs="+", help="FLAG=VALUE to set.  Valid "
                    "flags names are device dependent.  See the device "
                    "docs for details.")
    sp.set_defaults(func=device.set_flags)

    #---------------------------------------
    # device.get_engine command
    sp = infogrp.add_parser("get-engine", help="Get device engine version.",
                            description="Get device engine version. "
                            "May solve communications problems with the "
                            "device.")
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.get_engine)

    #---------------------------------------
    # device.get_model command
    sp = infogrp.add_parser("get-model", help="Get device model information.",
                            description="Get device model information.")
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.get_model)

    #---------------------------------------
    # device.on command
    sp = commandgrp.add_parser("on", help="Turn a device on.",
                               description="Turn a device on. Will not "
                               "trigger linked devices, see 'scene' for that.")
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
    # device.off command
    sp = commandgrp.add_parser("off", help="Turn a device off.",
                               description="Turn a device off.  Will not "
                               "trigger linked devices, see 'scene' for that.")
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
    # device.set command
    sp = commandgrp.add_parser("set", help="Turn a device to specific level.",
                               description="Turn a device to specific level. "
                               "Will not trigger linked devices.")
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
    # device.increment_up command
    sp = commandgrp.add_parser("up", help="Increments a dimmer up.",
                               description="Increments a dimmer up in 1/32 "
                               "steps. Will not trigger linked devices.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("-r", "--reason", metavar="reason", type=str, default="",
                    help="Reason message to send with the command.  No "
                    "message with use 'command'.")
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.increment_up)

    #---------------------------------------
    # device.increment_down command
    sp = commandgrp.add_parser("down", help="Decrements a dimmer down.",
                               description="Increments a dimmer down in 1/32 "
                               "steps. Will not trigger linked devices.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("-r", "--reason", metavar="reason", type=str, default="",
                    help="Reason message to send with the command.  No "
                    "message with use 'command'.")
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.increment_down)

    #---------------------------------------
    # device.scene command
    sp = commandgrp.add_parser("scene", help="Simulate a scene command.",
                               description="Simulate a scene command. "
                               "This triggers the device to react as though "
                               "its button was pressed, causing all linked "
                               "devices to react as well.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("-r", "--reason", metavar="reason", type=str, default="",
                    help="Reason message to send with the command.  No "
                    "message with use 'scene'.")
    sp.add_argument("-l", "--level", metavar="level", type=str, default=None,
                    help="The brightness level to set the device if supported."
                    " Otherwise on will be the defined scene level. Modem "
                    "does not support the level command.")
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
    sp = initgrp.add_parser("pair", help="Pair a device with the modem.",
                            description="Pair a device to the modem. "
                            "This adds all the necessary device->modem links, "
                            "so that the modem will be informed of changes on "
                            "the device. "
                            "This is generally the second thing you need "
                            "to do with a new device.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("address", help="Device address or name.")
    sp.set_defaults(func=device.pair)

    #---------------------------------------
    # device.db_add add ctrl/rspdr command
    sp = advancedgrp.add_parser("db-add", help="Add a link.",
                                description="Add the device/modem as the "
                                "controller or responder of another device.  "
                                "The addr1 input sets the device to modify.  "
                                "Also adds the corresponding entry on the "
                                "linked device unless --one-way is set.")
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
    sp = advancedgrp.add_parser("db-delete", help="Delete a link.",
                                description="Delete an entry in the device/"
                                "modem's all link database with the input "
                                "address, group, and mode.  Also deletes the "
                                "corresponding entry on the linked device "
                                "unless --one-way is set.")
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
    sp = configgrp.add_parser("set-button-led", help="Set the button LED "
                              "state for a KeyPadLinc.",
                              description="Set the button LED state for a "
                              "KeyPadLinc.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.add_argument("address", help="Device address or name.")
    sp.add_argument("group", type=int, help="Group (button) number to set")
    sp.add_argument("is_on", type=int, default=1, choices=[0, 1],
                    help="1 to turn the LED on, 0 to turn it off.")
    sp.set_defaults(func=device.set_button_led)

    #---------------------------------------
    # device.sync
    sp = linkgrp.add_parser("sync", help="Sync the scenes defined in "
                            "scenes.yaml with device.",
                            description="This will add or remove links on the "
                                        "device to match those defined in the "
                                        "scenes.yaml file.")
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
    sp = linkgrp.add_parser("import-scenes", help="Import all of the scenes "
                                                  "defined on the device into "
                                                  "the scenes.yaml file.",
                            description="This will add all links defined on "
                                        "the device to the scenes.yaml file. "
                                        "Any link defined in the scenes.yaml "
                                        "file that is not present on the "
                                        "device will be DELETED.")
    sp.add_argument("address", help="Device address or name.")
    sp.add_argument("--run", action="store_true", default=False,
                    help="Perform the actions altering the scenes config file "
                    " to bring it in sync.  If not specified, will perform a "
                    "dry-run which only lists the changes to be made.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.set_defaults(func=device.import_scenes)

    #---------------------------------------
    # device.awake
    # Only works on battery devices
    sp = batterygrp.add_parser("awake", help="Mark a battery device as being "
                               "awake.",
                               description="Mark a battery device as being "
                                           "awake. Necessary in order to send "
                                           "commands to the device in real "
                                           "time. Otherwise commands will be "
                                           "queued until the device is next "
                                           "awake. To wake up a battery "
                                           "device hold the set button on the "
                                           "device until the light blinks. "
                                           "The device will remain awake for "
                                           "~3 minutes.")
    sp.add_argument("address", help="Device address or name.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.set_defaults(func=device.awake)

    #---------------------------------------
    # device.get_battery_voltage
    # Only works on some battery devices
    sp = batterygrp.add_parser("get-battery-voltage", help="Check the battery "
                               "voltage.",
                               description="Check the battery voltage. Will "
                                           "request the value "
                                           "the nex time the device is awake.")
    sp.add_argument("address", help="Device address or name.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.set_defaults(func=device.get_battery_voltage)

    #---------------------------------------
    # device.set_low_battery_voltage
    # Only works on some battery devices, notably those with removable batts
    sp = batterygrp.add_parser("set-low-battery-voltage", help="Sets the "
                               "threshold voltage at which a battery will be "
                               "signaled as low.",
                               description="Sets the threshold "
                               "voltage at which a battery will be signaled "
                               "as low.")
    sp.add_argument("address", help="Device address or name.")
    sp.add_argument("voltage", type=float, help="Low voltage as float.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.set_defaults(func=device.set_low_battery_voltage)

    auto_int = lambda x: int(x, 0)

    #---------------------------------------
    # device.raw_message
    sp = advancedgrp.add_parser("raw-command", help="Sends a raw message to "
                                "the device.",
                                description="Sends a raw message to the "
                                            "device. Useful for testing "
                                            "features not yet supported")
    sp.add_argument("address", help="Device address or name.")
    sp.add_argument("cmd1", type=auto_int, help="cmd1 byte (supports "
                        "both hex and decimal)")
    sp.add_argument("cmd2", type=auto_int, help="cmd2 byte (supports "
                        "both hex and decimal)")
    sp.add_argument("--ext-req", action="store_true", help="Send message "
                        "as an extended message")
    sp.add_argument("--ext-resp", action="store_true", help="Receive response "
                    "as an extended message")
    sp.add_argument("-d", "--data", type=auto_int, default=None, nargs="*",
                        help="the extended message data (supports both hex "
                        "and decimal)")
    sp.add_argument("--crc", type=str, choices=["D14", "CRC"])
    sp.add_argument("-q", "--quiet", action="store_true",
                        help="Don't print any command results to the screen.")
    sp.set_defaults(func=device.send_raw_command)

    #---------------------------------------
    # modem.factory_reset command
    sp = advancedgrp.add_parser("factory-reset", help="Perform a remote "
                                "factory reset.  Currently only supported on "
                                "the modem.",
                                description="Perform a remote factory "
                                "reset.  Currently only supported on the "
                                "modem.")
    sp.add_argument("-q", "--quiet", action="store_true",
                    help="Don't print any command results to the screen.")
    sp.set_defaults(func=modem.factory_reset)

    return p.parse_args(args)


#===========================================================================
def main(mqtt_converter=None):
    args = parse_args(sys.argv[1:])

    # Validate the configuration file
    val_errors = config.validate(args.config)
    if val_errors != "":
        return val_errors

    # Load the configuration file.
    cfg = config.load(args.config)

    topic = cfg.get("mqtt", {}).get("cmd_topic", None)
    if topic:
        args.topic = topic

    return args.func(args, cfg)

#===========================================================================
