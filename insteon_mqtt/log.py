#===========================================================================
#
# Logging utilities
#
#===========================================================================
import logging
import logging.handlers

# Add a custom logging level.  This lets us do some filtering for sending
# user interface messages to the command line tool about command status and
# progress that are nicer than the raw logging messages.
UI_LEVEL = 21
logging.addLevelName(UI_LEVEL, "UI")


#===========================================================================
def get_logger(name="insteon_mqtt"):
    """Get a logger object to use.

    This will return a logging object to use for messages.

    Args:
      name (str):  The name of the logging objectd.

    Returns:
      The requested logging object.
    """
    # Force the logging system to use our custom logger class, then restore
    # whatever was set when we're done.
    save = logging.getLoggerClass()
    try:
        logging.setLoggerClass(Logger)
        return logging.getLogger(name)
    finally:
        logging.setLoggerClass(save)


#===========================================================================
def initialize(level=None, screen=None, file=None, config=None):
    """Initialize the logging settings.

    Args:
      level (int):  The logging level to set.
      screen (bool):  True to turn on logging to the screen.  False to turn it
             off.  If None, the default of True is used.
      file (str): File to log to or None to skip.
      config:  Config object to read logging information from.  This read from
               the yaml file and the 'logging' key is extracted to configure
               the inputs.
    """
    # Config variables are used if the config is input and if a direct input
    # variable is not set.
    if config:
        # Read the logging config and initialize the library logger.
        data = config.get("logging", {})

        if level is None:
            level = data.get("level", None)
        if screen is None:
            screen = data.get("screen", None)
        if file is None:
            file = data.get("file", None)

    # Apply defaults if none were set.
    level = level if level is not None else logging.INFO
    screen = bool(screen) if screen is not None else True
    file = file if file is not None else None

    # Set the logging level into the library logging object.
    log_obj = get_logger()
    log_obj.setLevel(level)

    # Add handlers for the optional screen and file output.
    fmt = '%(asctime)s %(levelname)s %(module)s: %(message)s'
    datefmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter(fmt, datefmt)

    if screen:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        log_obj.addHandler(handler)

    if file:
        # Use a watched file handler - that way LINUX system log
        # rotation works properly.
        handler = logging.handlers.WatchedFileHandler(file)
        handler.setFormatter(formatter)
        log_obj.addHandler(handler)


#===========================================================================
class Logger(logging.getLoggerClass()):
    """Custom logging class.

    This allows us to have a custom ui() function for logging.  The ui level
    can set a callback function which is run when UI messages are logged.
    This let's us send back specific user interface messages to the remote
    command line tool for a nicer interface.
    """
    def __init__(self, name):
        """Constructor

        Args:
          name (str):  The logging objecst name.
        """
        super().__init__(name)
        self._ui_handler = None

    #-----------------------------------------------------------------------
    def ui(self, msg, *args, **kwargs):
        """Log a UI level message.

        API is the same as standard logging messages.

        Args:
           msg (str): The message to log.
           args:  Optional arguments.
           kwargs:  Optional keyword arguments.
        """
        if self.isEnabledFor(UI_LEVEL):
            self._log(UI_LEVEL, msg, args, **kwargs)

    #-----------------------------------------------------------------------
    def set_ui_callback(self, callback):
        """Add a callback for UI messages.

        The callback will be passed the logging module Record object to
        process when a UI message is logged.  Only one UI callback can be
        added at a time.

        Args:
          callback:  The callback function to use.
        """
        self._ui_handler = CallbackHandler(callback)
        self.addHandler(self._ui_handler)

    #-----------------------------------------------------------------------
    def del_ui_callback(self):
        """Remove the UI callback handler.
        """
        self.removeHandler(self._ui_handler)

    #-----------------------------------------------------------------------

#===========================================================================


class CallbackHandler(logging.Handler):
    """Logging handler object.

    This will call the input function with the logging record.  This
    basically forwards logging record calls to an arbitrary python function.
    """
    def __init__(self, callback):
        """Constructor

        Args:
          callback:  The callback function to use.
        """
        super().__init__(UI_LEVEL)
        self.callback = callback

    #-----------------------------------------------------------------------
    def emit(self, record):
        """Handle a logging record.

        Args:
           record:  The logging record.
        """
        self.callback(record)

#===========================================================================
