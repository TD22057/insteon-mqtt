Test utilities

tests/conftest.py adds this to the pythonpath so it can be used in the test
cases.

pytest.ini sets an option to insure this directory isn't scanned for tests.

All imports are in a helpers directory here so that we can import by module
and know where it came from.
