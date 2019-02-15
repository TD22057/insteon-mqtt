# Insteon-MQTT Bridge Quick Start

This package assumes that you:

- Have a working MQTT broker up and running.  If not, do that first
  ([Mosquitto](https://mosquitto.org/) is good choice).

- Have an Insteon PLM modem (serial or USB) or one of the older hubs that
  supports a PML port (usually 9761) on a fixed IP address.

- Have a working Python 3 installation on on your machine.  Modern
  Debian and Ubuntu installations should already have this but you may
  need to do:

  ```
  sudo apt update
  sudo apt install python3-dev python3-pip
  sudo pip3 install --upgrade virtualenv wheel
  ```

  If you python 3 version is < 3.3, you may also need to do `sudo apt-install
  python3-venv`

- Have read access to the serial/USB line the modem is connected to.
  On Ubuntu, this means your user should be a member of the dialout
  group.

   ```
   sudo adduser $USER dialout
   ```

1) Clone the repository to your local machine via zip download or using git:

   ```
   git clone 'https://github.com/TD22057/insteon-mqtt.git'
   ```

2) Create a virtual-env to use for all the dependencies to avoid
   installing in the system directories.  The virtual env directory
   'venv' can be named anything or placed anywhere (I use
   /opt/insteon-mqtt).  The install the package and its dependencies.

   ```
   cd insteon-mqtt
   python3 -m venv venv
   source venv/bin/activate
   pip install .
   ```

3) Edit the configuration file `config.yaml`.  You may want to make a
   copy and place it in the virtual env directory or somewhere like
   /etc/insteon-mqtt.yaml.

   - Set the Insteon port to be the USB port or address of the PLM modem.
   - Set the modem Insteon hex address (printed on the back of the modem).
   - Edit the Insteon device section and enter the hex addresses of all
     the devices you have.
   - Edit the storage location.  Each device will save it's database in
     this directory.
   - Edit the MQTT topics and payload section.  The sample config.yaml file
     is designed for integration with Home Assistant but you can change it
     to use whatever style of messages you want.

4) Start the server.  You will see a bunch of logging messages shown
   on the screen.  Assuming everything is OK, it will then just sit
   there.

   ```
   source venv/bin/activate
   insteon-mqtt config.yaml start
   ```

5) Join, Pair, and Sync each device in your network.  This can be accomplished
   using mqtt messages as described in the [Required Device Initialization]
  (mqtt.md#required-device-initialization) section.

  ```
  insteon-mqtt config.yaml join aa.bb.cc
  insteon-mqtt config.yaml pair aa.bb.cc
  insteon-mqtt config.yaml sync aa.bb.cc
  ```

6) Download an Insteon device database for every device.  This may
   take awhile and battery operated devices (motion sensors, remotes,
   etc) will fail because they aren't awake.

   ```
   insteon-mqtt config.yaml refresh-all
   ```

   Once that finishes, you should wake up each battery powered device
   (by activating it or pressing the set button - it may depend on the
   device) and then quickly send a command to the Insteon hex address
   of that device to download the database (hopefully this will be
   automatic in the future).

   ```
   insteon-mqtt config.yaml refresh AA.BB.CC
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

   ```
   insteon-mqtt config.yaml pair AA.BB.CC
   ```

   Downloading the device database and pairing only needs to be done
   one time.  The refresh command only needs to be sent again if you
   make changes to the Insteon links (scenes) manually without using
   the server.

7) You can monitor the devices to make sure things are working by
   watching MQTT messages.  With mosquitto, you can run the following to
   see every messages being sent in and out of the server.

   ```
   mosquitto_sub -v -t 'insteon/#'
   ```

8) To command devices, you can use the command line tool or send MQTT
   messages.  For example, to turn on a light, both of these will have
   the same affect:

   ```
   insteon-mqtt config.yaml on AA.BB.CC
   mosquitto_pub -t 'insteon/command/AA.BB.CC' -m '{ "cmd" : "on" }'
   ```

   For a dimmer device, add the level:

   ```
   mosquitto_pub -t 'insteon/command/AA.BB.CC' -m '{ "cmd" : "on", "level" : 128 }'
   ```

   Run `insteon-mqtt -h` to see all the commands that can be sent.

---

After you have the basics working, you may want to consult:

- [Detailed device documentation](mqtt.md) for information on
  device configuration and available MQTT commands and options.

- [System install and automatically starting the
  server](auto_start.md) on boot.
