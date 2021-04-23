# Initializing Insteon Devices

When setting up Insteon-MQTT, adding a new device, or to solve problems, it is necessary to run a series of commands to initialize a device.  _For most users, once they complete the `join`, `pair`, `refresh` sequence on a device, they never have to use those functions on that device again._

> Please see, [User Interfaces](user_interface.md), for details on how to interact with Insteon-MQTT using the _Command Line_, _MQTT_, or _WebGUI_ interfaces.

All of these functions are idempotent, they can be run multiple times without causing any issue.

> __Note__ Battery devices (e.g. motion sensors, remotes, etc) are normally sleeping and will not respond to commands sent to them.  If the commands below are sent to a battery device, the command will be queued and will attempt to be run the next time the device is awake. For more details, see [battery devices](battery_devices.md)

1. __Join__ This is necessary to allow the modem to talk to the device.  This needs to be done first on any new device or device that has been factory reset.  If you are seeing the error `Senders ID not in responders db. Try running 'join' again.`
   - To join a __single device__ run `join`.

    _Command Line_
    ```
    insteon-mqtt config.yaml join aa.bb.cc
    ```
    _MQTT_
    ```
    Topic: /insteon/command/aa.bb.cc
    Payload: { "cmd" : "join" }
    ```

   - To join __all__ devices run `join_all`.  This may be necesary when first setting up a network.

     _Command Line_
     ```
     insteon-mqtt config.yaml join-all
     ```
     _MQTT_
     ```
     Topic: /insteon/command/modem
     Payload: { "cmd" : "join_all" }
     ```

2. __Pair__ - This adds links to the device so that the device knows to notify the modem of state changes.  If you do not see any activity in Insteon-MQTT when you manually activate a device, you should try running `pair` again.

   - To pair a __single device__ run `pair`.

    _Command Line_
    ```
    insteon-mqtt config.yaml pair aa.bb.cc
    ```
    _MQTT_
    ```
    Topic: /insteon/command/aa.bb.cc
    Payload: { "cmd" : "pair" }
    ```

   - To pair __all__ devices run `pair_all`.  This may be necesary when first setting up a network.

      _Command Line_
      ```
      insteon-mqtt config.yaml pair-all
      ```
      _MQTT_
      ```
      Topic: /insteon/command/modem
      Payload: { "cmd" : "pair_all" }
      ```

3. __Refresh__ - This downloads the 1) device link database, if necessary; 2) model information, if necessary; 3) the current state (e.g. on/off); and 4) other relevant details from the device.  It may take a few seconds per device to complete all of these steps.
  - `force` - this flag will cause the link database of to be refreshed even if it appears that our cached data is current.

  >If the device state is updated as a result of a `refresh` command the [reason](reason.md) string will be set to 'refresh'

 > If you manually add links to the device (e.g. by using some other device such as an ISY, or by using the set buttons on the device) you will need to run `refresh` again so that Insteon-MQTT can learn about these links.

   - To refresh a __single device__ run `refresh`.

    _Command Line_
    ```
    insteon-mqtt config.yaml refresh aa.bb.cc [--force]
    ```

    _MQTT_
     ```
     Topic: /insteon/command/aa.bb.cc
     Payload: { "cmd" : "refresh", ["force" : true/false] }
     ```

   - To refresh __all__ devices run `refresh_all`.  This may be necesary when first setting up a network.  __This may take a while to complete__

    _Command Line_
     ```
     insteon-mqtt config.yaml refresh-all [--force]
     ```

    _MQTT_
     ```
     Topic: /insteon/command/modem
     Payload: { "cmd" : "refresh_all", ["force" : true/false] }
     ```

## Scene Commands

The above functions are all that is needed for an initial setup.  If you have scenes defined in a `scenes.yaml` file, you will need to run the `sync` or `sync_all` commands as described in [scenes](scenes.md).
