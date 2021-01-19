# Development Guide

# Set Up

   ```
   git clone https://github.com/TD22057/insteon-mqtt.git
   cd insteon-mqtt
   python3 -m venv venv
   source venv/bin/activate
   pip3 install -r requirements.txt
   pip3 install -r requirements-test.txt
   ```

# Branches

The main development is done on the `dev` branch.  Stable releases are
on the master branch.  Do NOT submit pull requests against the master
branch.  Be sure to checkout the dev branch and base all pull requests
against that.


# Coding Style

- All of the code must follow pep8 style and be checked with flake8 and
  pylint.  These must be run from the top level directory of the repository.

   ```
   flake8 ./insteon_mqtt
   pylint ./insteon_mqtt
   ```

- Classes, functions, and methods must be documented with Python
  docstrings in the Google style.  Look at existing code if you need
  an example.  Future versions will include a sphinx generated HTML
  documentation build.


# Unit Tests

Unit tests should be added in the tests directory and run before
submitting any code.  The goal should be 100% code coverage (I'm
still working on this one myself).

Tests can be executing by running `pytest` from the top directory.  To run a
single test, pass the file name to pytest on the command line.

   ```
   pytest
   pytest tests/tests_Address.py

   # Show log messages while testing
   pytest -s -vv --log-cli-level=10 tests/mqtt/test_Outlet.py
   ```

Coverage testing shows which lines needs to have test cases added and can be
run with the --cov flag.  The html option will create an `htmlcov` directory
that contains html files that graphically show which lines need to have tests
added.

   ```
   # Show lines that need coverage
   pytest --cov=insteon_mqtt --cov-report term-missing

   # Create html files that show missing lines
   pytest --cov=insteon_mqtt --cov-report html
   ```

# Logging

The user interface is entirely driven by log messages, so some care has to be
taken to select the proper logging levels.  The following are some
suggestions.

1. `LOG.exception()` This will generate a `LOG.error()` message, and will
output a traceback to the log.  This should be used if the source of the error
is unknown and a traceback would be helpful to diagnose the source.
2. `LOG.error()` This will generate a message sent to the User Interface.
This should be used if the users command cannot be carried out.
3. `LOG.warning()` This will generate a message sent to the User Interface.
This should be used to warn a user that some anomaly happened, but it probably
didn't interfere with their request.
4. `LOG.UI()` This will generate a message sent to the User Interface.  This
should be used to give direct User Interface responses.  Generally, these are
expected successful responses.
5. `LOG.info()` This will only generate a message in the log.  This should
be used for assisting in debugging.  These should generally include valuable
information such as the translation of a value or message into something
readable.
6. `LOG.debug()` This will only generate a message in the log.  This should
be used for truly verbose logging.  Messages that say nothing more than "we
made it to this point in the code" should go here.

Log levels `Error, Warning, and UI` __are all outputted to the user
interface__, while `exception, debug, and info` __are only written to the
log__.  So please take into account your audience when selecting a log level
and the content of  the log message.

Generally, unless you intend to catch an Exception somewhere else in the code
do not use the generic `raise Exception` as this will only produce an
exception and traceback in the log, but will not produce any other logging
message.  Consider using `LOG.exception()` instead.
