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
