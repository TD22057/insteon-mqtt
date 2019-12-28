# Insteon-MQTT Bridge Quick Start for Hass.io users

## First time installation

This package assumes that you:

- Have a hass.io installation up and running with either SSH access or a
  network share.

- Have a working MQTT broker up and running.  If not, do that first
  ([Mosquitto](https://mosquitto.org/) is good choice, and has [an addon for
  hass.io](https://www.home-assistant.io/addons/mosquitto/)).

- Have an Insteon PLM modem (serial or USB) or one of the older hubs that
  supports a PML port (usually 9761) on a fixed IP address.

- Have hass.io connected to your mqtt broker.

1) Create a directory for insteon-mqtt in your /addons folder:
   `mkdir /addons/insteon-mqtt`

2) Copy the `hassio/config.json` from this repository into
   `/addons/insteon-mqtt/config.json` on your hass.io device.

3) Install the Local Insteon MQTT addon through the hass.io addon store.
  * If you do not see the 'Local Add-ons' repository or the Insteon MQTT
    add-on, click the refresh button in the top right corner on the Hass.io
    Add-ons page, and it should show up.

4) Start the addon. This will setup the default config files under
   `/config/insteon-mqtt/config.yaml`.

5) Edit `/config/insteon-mqtt/config.yaml` as appropriate.

   - Set the Insteon port to be the USB port or address of the PLM modem.
   - Set the modem Insteon hex address (printed on the back of the modem).
   - Edit the Insteon device section and enter the hex addresses of all
     the devices you have.
   - Edit the storage location.  Each device will save it's database in
     this directory.
   - Edit the MQTT topics and payload section.  The sample config.yaml file
     is designed for integration with Home Assistant but you can change it
     to use whatever style of messages you want.

6) Restart the insteon-mqtt addon to pick up the changes.

7) Join, Pair, and Sync each device in your network.  This can be accomplished
   using mqtt messages as described in the
   [Required Device Initialization](mqtt.md#required-device-initialization)
   section.

8) Download an Insteon device database for every device.  This may
   take awhile and battery operated devices (motion sensors, remotes,
   etc) will fail because they aren't awake. Publish the following command
   to `insteon/command/modem`

   ```
   { "cmd": "refresh_all", "force": false }
   ```

   Once that finishes, you should wake up each battery powered device
   (by activating it or pressing the set button - it may depend on the
   device) and then quickly send a command to the Insteon hex address
   of that device to download the database (hopefully this will be
   automatic in the future). Publish the following command to
   `insteon/command/aa.bb.cc`

   ```
   { "cmd": "refresh", "force": false }
   ```

   If you haven't linked the device as a controller of the modem
   (press set on the device, then set on the modem), you'll also need
   to tell the device to pair with the modem.  This step is also
   needed for complicated devices like the smoke bridge which require
   multiple Insteon groups to be configured.

   IMPORTANT: If you do not call pair for each device one time (it only needs
   to be done once) means that the correct controller/responder links from
   the device to the PLM modem may not exist and the functionality of the
   device with the Insteon-MQTT system may not work until pair() is called.

   Publish the following command to `insteon/command/aa.bb.cc`
   ```
   { "cmd": "pair" }
   ```

   Downloading the device database and pairing only needs to be done
   one time.  The refresh command only needs to be sent again if you
   make changes to the Insteon links (scenes) manually without using
   the server.

## Updating

To update, replace your `/addons/insteon-mqtt/config.json` with the most
recent `hassio/config.json
