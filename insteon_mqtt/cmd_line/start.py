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
    stack_link = network.Stack()

    # Setup the PLM or Hub
    use_hub = cfg['insteon'].get('use_hub', False)
    time_out = None
    if use_hub:
        # This reduces the time that the select/poll call will block. The
        # default of None is 3 seconds.  A half a second is the same speed at
        # which we query the hub for incoming messages. If that rate is
        # changed, consider changing this as well.
        time_out = .5
        plm_link = network.Hub()
        loop.add_poll(plm_link)
    else:
        plm_link = network.Serial()
        loop.add(plm_link, connected=False)

    # Add Stack and timed
    stack_link = network.Stack()
    timed_link = network.TimedCall()

    # Add the clients to the event loop.
    loop.add(mqtt_link, connected=False)
    loop.add_poll(stack_link)
    loop.add_poll(timed_link)

    # Create the insteon message protocol, modem, and MQTT handler and
    # link them together.
    insteon = Protocol(plm_link)
    modem = Modem(insteon, stack_link, timed_link)
    mqtt_handler = mqtt.Mqtt(mqtt_link, modem)

    # Load the configuration data into the objects.
    config.apply(cfg, mqtt_handler, modem)

    # Start the network event loop.
    while loop.active():
        loop.select(time_out=time_out)
