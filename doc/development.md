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

- All of the code must follow pep8 style and be checked with flake8
  and pylint.

   ```
   flake8 insteon-mqtt
   pylint insteon-mqtt
   ```

- Classes, functions, and methods must be documented with Python
  docstrings in the Google style.  Look at existing code if you need
  an example.  Future versions will include a sphinx generated HTML
  documentation build.


# Unit Tests

Unit tests should be added in the tests directory and run before
submitting any code.  The goal should be 100% code coverage (I'm
still working on this one myself).

Tests can be executing by running `pytest` from the top directory.