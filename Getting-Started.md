## Getting Started with Insteon-MQTT in Debian Jessie

### Installing Required Dependencies and Software
1. Update your repositories: `apt update`
1. Install Python 3 and pip: `apt install python3 python3-pip`
1. Install required Python libraries: `pip3 install pyserial Jinja2 paho-mqtt pyyaml`
1. Install Git (if pulling insteon-mqtt directly from github): `apt install git`
1. Download latest copy of insteon-mqtt: `git clone https://github.com/TD22057/insteon-mqtt.git`
1. Ensure you have an MQTT broker installed as well as `mosquitto_sub` and `mosquitto_pub` for testing.

### Configure Insteon-MQTT config.yaml file
- Set `port: "/dev/ttyUSB0"` or whatever the correct serial port is for your PLM
- Set `address: xx.xx.xx` to the Insteon address of your PLM (printed on a label on the back of the PLM)
- Set `startup_refresh: True` You may want to change this later if you have a large number of Insteon devices as it will create a bit of traffic on your Insteon network as each device is polled when you start insteon-mqtt but for now at least you probably want this enabled.
- Configure an Insteon switch or dimmer device in the appropriate section of the configuration as indicated in the configuration file.
- Ensure you have an MQTT broker running on the localhost or update the broker and port in the configuraiton file.

### Set the Python location in run.py
Edit the first line of `run.py` to be `#!/usr/bin/python3`

### Test Functionality of Insteon-MQTT
1. Start `./run.py`
1. In a new terminal window run `mosquitto_sub -v -t "insteon/#"` You should see state status messages for all the devices you configured in config.yaml
1. In a new terminal window try turning on a device `mosquitto_pub -t "insteon/xx.xx.xx/set" -m '{ "state" : "on" }'` (replacing xx.xx.xx with the device's Insteon address). Verify the device has turned on and that the reported MQTT state has changed.
1. In a new terminal window try turning off a device `mosquitto_pub -t "insteon/xx.xx.xx/set" -m '{ "state" : "off" }'` (replacing xx.xx.xx with the device's Insteon address). Verify the device has turned on and that the reported MQTT state has changed.
1. If you have a dimmer device try setting a level between 0-255 like `mosquitto_pub -t "insteon/xx.xx.xx/set" -m '{ "state" : "on" , "brightness" : 128 }'`


