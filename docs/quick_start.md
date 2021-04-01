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

3) Copy the `config-example.yaml` file.  You should make a copy named `config.yaml`.  Keep the original file for reference.  You may want to place the `config.yaml` place it in the virtual env directory or somewhere like
   /etc/insteon-mqtt.yaml.

4) Edit the `config.yaml` file. See [configuration](configuration.md) for more detailed instructions.

5) Start the server.  You will see a bunch of logging messages shown
   on the screen.  Assuming everything is OK, it will then just sit
   there.

   ```
   source venv/bin/activate
   insteon-mqtt config.yaml start
   ```

6) Initialize your devices, see [initializing](initializing.md)

## Additional Resources

- [User Interfaces](user_interface.md) for information on how to interact with Insteon-MQTT

- [Debugging](debugging.md) for information on how to diagnose problems.

- [Device documentation](mqtt.md) for information on
  device configuration and available MQTT commands and options.

- [System install and automatically starting the   server](auto_start.md) on boot.
