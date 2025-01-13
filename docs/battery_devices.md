# Battery Devices

Battery devices (e.g. motion sensors, remotes, etc) are normally sleeping and will not respond to commands sent to them.  If you send a commands to a battery device, the command will be queued and will attempt to run the next time the device is awake.

> As noted below, not all devices enter an _awake_ state after sending a message.  For some devices, the only option is to manually wake them up.

## `*_all` Commands
None of the `*_all` style commands will work on battery devices, you must individually call the commands you wish to run on each battery device.

## Waking a Battery Device

### Automatically

For many of the newer battery devices, they automatically wake up for a short period of time after the device sends a message.  You can trigger a message by activating the device (e.g. walk in front of a motion sensor, press a button on a remote). When this happens, Insteon-MQTT will attempt to send all queued messages to the device.  The device is only awake for a very short period of time (seconds). So this doesn't always work.

> Not all battery devices wake up automatically.

### Manually

For those battery devices that do not automatically wake up, or are difficult to communicate with in such a short period of time, you can manually wake them up.  To do this hold in the set button on the device until the device light flashes or you hear a beep.  At this point they will stay awake for approximately 3 minutes.

If you manually wake up a device using this method, then call this command so that the Insteon-MQTT knows that it can send messages to the device for the next three minutes.

  _Command Line_
  ```
  insteon-mqtt config.yaml awake aa.bb.cc
  ```


  _MQTT_
  ```
  Topic: /insteon/command/aa.bb.cc
  Payload: { "cmd": "awake" }
  ```
