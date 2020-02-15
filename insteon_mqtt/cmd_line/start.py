#===========================================================================
#
# Start the main server
#
#===========================================================================
from .. import config
from .. import log
from .. import mqtt
from .. import network
from ..Modem import Modem
from ..Protocol import Protocol


def start(args, cfg):
    """Main start command

    This will start the main MQTT<->Insteon bridge and never return.

    Args:
      args:  The command line arguments.
      cfg:   The configuration dictionary.
    """
    # Always log to the screen if a file isn't active.
    if not args.log:
        args.log_screen = True

    # Initialize the logging system either using the command line
    # inputs or the config file.  If these vars are None, then the
    # config file logging data is used.
    log.initialize(args.level, args.log_screen, args.log, config=cfg)

    # Create the network event loop and MQTT and serial modem clients.
    loop = network.Manager()
    mqtt_link = network.Mqtt()
    plm_link = network.Serial()
    stack_link = network.Stack()

    # Add the clients to the event loop.
    loop.add(mqtt_link, connected=False)
    loop.add(plm_link, connected=False)
    loop.add(stack_link, connected=True)

    # Create the insteon message protocol, modem, and MQTT handler and
    # link them together.
    insteon = Protocol(plm_link)
    modem = Modem(insteon, stack_link)
    mqtt_handler = mqtt.Mqtt(mqtt_link, modem)

    # Load the configuration data into the objects.
    config.apply(cfg, mqtt_handler, modem)

    # Start the network event loop.
    while loop.active():
        loop.select()
