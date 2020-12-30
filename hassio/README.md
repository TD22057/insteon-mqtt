# Home Assistant Add-on: Insteon MQTT
This add-on provides an MQTT interface to Insteon devices.

## Requirements
1. An Insteon PLM or Hub
2. Some Insteon devices
3. An MQTT broker.  The Mosquitto broker in the Add-on store works great

## Installation
1. Navigate in Home Assistant frontend to __Supervisor -> Add-on Store__
2. Select the menu in the top right and click __Repositories__
3. Paste the following URL into the __Add Repository__ field:
   `https://github.com/TD22057/insteon-mqtt`
4. Click __ADD__
5. Scroll to find the __Insteon MQTT Repository__
6. Click on the __Insteon MQTT__ Add on
7. Click __Install__
8. Edit the configuration file at `/config/insteon-mqtt/config.yaml`
9. Click __Start__ to start the Add-on
