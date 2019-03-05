#===========================================================================
#
# pytest setup configuration file.
#
# pylint: disable=wrong-import-position
#===========================================================================
import os
import sys
import pytest

# Add the helpers dir to the python path so tests can easily import the
# helpers module which contains common test code.
sys.path.append(os.path.join(os.path.dirname(__file__), 'util'))
import helpers as H  # noqa: E402


#===========================================================================
#
# Test fixtures
#
#===========================================================================
@pytest.fixture
def mock_paho_mqtt():
    """Mock out the paho MQTT client.

    Use this as a test fixture and it will patch paho.mqtt.client.Client to
    be heplers.MockNetwork_MqttClient and then restore when exiting.  See
    tests/mqtt/test_BatterySensory for an example.
    """
    # Monkey patch paho.mqtt.Client to return self when constructed
    import paho.mqtt.client
    save = paho.mqtt.client.Client
    paho.mqtt.client.Client = H.network.MockMqttClient
    yield

    # Code that runs after the test is done - restore the paho module to it's
    # original state.
    paho.mqtt.client.Client = save

#===========================================================================
