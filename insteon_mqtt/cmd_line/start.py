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
    """TODO: doc
    """
    # Initialize the logging system either using the command line
    # inputs or the config file.  If these vars are None, then the
    # config file logging data is used.
    log_screen, log_file = None, None
    if args.log == 'stdout':
        log_screen = True
    elif args.log:
        log_file = args.log

    log.initialize(args.level, log_screen, log_file, config=cfg)

    # Create the network event loop and MQTT and serial modem clients.
    loop = network.Manager()
    mqtt_link = network.Mqtt()
    plm_link = network.Serial()

    # Add the clients to the event loop.
    loop.add(mqtt_link, connected=False)
    loop.add(plm_link, connected=False)

    # Create the insteon message protocol, modem, and MQTT handler and
    # link them together.
    insteon = Protocol(plm_link)
    modem = Modem(insteon)
    mqtt_handler = mqtt.Mqtt(mqtt_link, modem)

    # Load the configuration data into the objects.
    config.apply(cfg, mqtt_handler, modem)

    # Start the network event loop.
    while loop.active():
        loop.select()
