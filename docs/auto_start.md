# System install and automatically starting the server

Start by installing python3 on the system.

   ```
   sudo apt update
   sudo apt install python3-dev python3-pip
   sudo pip3 install --upgrade virtualenv
   ```

Download the latest release copy of the software.

   ```
   cd $HOME
   git clone https://github.com/TD22057/insteon-mqtt.git
   ```

Create a user and group. Give the user access to serial line so that
it can talk to the modem.  System services should never run as root so
this is a dummy user used to just run the server.

   ```
   sudo adduser --system insteon
   sudo addgroup insteon
   sudo adduser insteon dialout
   ```

Create a directory to install the package in and set it’s ownership
and permissions.  Then change to the new insteon user to finish the
installation.

   ```
   sudo mkdir /opt/insteon-mqtt
   sudo chown insteon:insteon /opt/insteon-mqtt
   sudo su -s /bin/bash insteon
   ```

Install a virtual env to sandbox the software and dependencies and
activate it so further installs are done here.

   ```
   cd /opt/insteon-mqtt
   python3 -m venv /opt/insteon-mqtt
   source bin/activate
   ```

Install the software from the downloaded (or git clone'd) directory.
You may get some pip errors complaining about bdist_wheel but those
can be ignored.

   ```
   cd $HOME/insteon-mqtt
   pip3 install .
   ```

Copy the configuration file to the install location.  Edit it to add
your insteon devices and configure your MQTT settings.  Also update
the storage directory to point at '/opt/insteon-mqtt/data'.  You may
also want to update the log file locations as well.

   ```
   cp config.yaml /opt/insteon-mqtt/config.yaml
   cd /opt/insteon-mqtt/
   mkdir data
   nano config.yaml
   ```

Try running the server to make sure it will start up.  Once it's
running OK, stop the process (ctrl-c), and exit the insteon-mqtt user
back to your regular user.

   ```
   insteon-mqtt config.yaml start
   [ctrl-c]
   exit
   ```

Edit the init/insteon-mqtt.service file with the installation path and
copy it to the systemd directory.  If your system is using something
besides systemd, you'll need to use a different file (and commands)
that what is provided.

   ```
   cd $HOME/insteon-mqtt
   nano init/insteon-mqtt.service
   [update paths if needed]
   sudo cp init/insteon-mqtt.service /etc/systemd/system/
   ```

Reload the service database and try and start the service.  Use the
status command to check the results.

   ```
   sudo systemctl --system daemon-reload
   sudo systemctl start insteon-mqtt
   sudo systemctl status insteon-mqtt
   ```

If everything looks OK, enable the service to start at the next boot.

   ```
   sudo systemctl enable insteon-mqtt
   ```
You can view the system logs for the process after the service is 
enabled with this journalctl command (or by manually looking at the 
log file).

   ```
   sudo journalctl -u insteon-mqtt.service -f
   ```
