# Revision Change History

## [0.6.5]

### Fixes
- Added better messages when the pair command fails because the modem db
  is out of date ([Issue #69][I69]).

- Updated docs and example config file because of breaking HomeAssistant
  MQTT light change for dimmers ([Issue #88][I88]).

### Additions
- New command 'get_model' added to the command line tool to retrieve and save
  the Insteon device cat, sub_cat, and firmware revision (thanks @krkeegan).
  ([Issue #55][I55]).

- New command 'join' added to the command line tool to perform a two-way
  pairing and refresh to link a device to the modem.  This combines the
  previous linknig and pair command into a single command (thanks @krkeegan).
  ([Issue #97][I97]).

- New improved NAK error response codes makes it easier to understand errors
  when the devices can't communicate (thanks @krkeegan).  ([Issue #95][I95]).

## [0.6.4]

### Additions
- Added on_level flag support for dimmers and KeyPadLinc's to set the light
  level when the on button is pressed ([Issue #70][I70]).

### Fixes
- Multiple output messages queued to the Insteon devices causes some messages
  to be lost ([Issue #86][I86]).

## [0.6.3]

### Additions
- Added on_level flag support for dimmers and KeyPadLinc's to set the light
  level when the on button is pressed ([Issue #70][I70]).

### Breaking Changes
- KeypadLinc now supports both dimmer and on/off device types.  This required
  changing the KeypadLinc inputs in the MQTT portion of the config.yaml file.
  See the file in the repository for the new input fields ([Issue #33][I33]).

### Additions
- HassIO and docker support and is now available.  See the main doc page for
  a link to the docs (thanks @lnr0626) ([Issue #63][I63], [PR #76][I76]).

- Added on/off outlet support ([Issue #48][I48]).

- Added support for older I1 devices (thanks @krkeegan).  This should allow
  refresh command and database manipulation for 5+ year old devices.
  ([Issue #17][I17]).

- Added support for automatic maximum hop computations in messages.  This
  should reduce delays and load on the insteon network  (thanks @krkeegan).
  ([Issue #43][I43]).

- Added support for waiting to write messages until the maximum number of
  hops have elapsed.  This should reduce subtle bugs where the Insteon
  network could get overloaded by sending messages to quickly.
  (thanks @krkeegan). (Issue #45][I45]).

## [0.6.2]

### Additions
- Added leak sensor heartbeat reporting support (thanks @djfjeff).

- Added get_engine() command to find the Insteon device engine revision
  (thanks @krkeegan).

- Added automatic message de-duplication (thanks @krkeegan)


### Fixes
- Fixed a bug where the MQTT client might close in an area that triggered an
  exception instead of a reconnect ([Issue #32][I32]).

- Fixed bug where the KeypadLinc was using the wrong handler for input MQTT
  scene simulation commands ([Issue #34][I34]).

- Fixed bug where the FanLinc would not report speed changes at all
  ([Issue #37][I37]).

- Fixed issues with the leak sensor topic documentation (thanks @djfjeff).

- Fixed a bug in the command line script that would not read the MQTT user
  name from the config.yaml file ([Issue #59][I59]).

## [0.6.1]

### Fixes
- Fixed ordering of config.yaml in command line examples ([Issue #27][I27]
  and [Issue #28][I28]).

- Changed default retain flag to True in config file ([Issue #29][I29]).


### Additions
- Switch, Dimmer, and KeypadLinc LED backlight levels can be changed with the
  set-flags command using the keyword "backlight" ([Issue #13][I13]).


## [0.6]

### Additions
- Battery powered devices will now attempt to download the all link
  database if it doesn't exist locally when a broadcast message from
  that device is seen (since the device is awake).  This way you can
  trip a battery device (motino sensor or push a remote button) and it
  will initiate a database download.

- Added FanLinc support ([Issue #4][I4]).  Thanks to @masterdka for testing.

- Added battery powered sensors (door and window sensors) support
  ([Issue #5][I5]).

- Added leak sensor support ([Issue #6][I6]).

- Added KeypadLinc support ([Issue #8][I8]).

- Added IOLinc support  ([Issue #12][I12]).

- Added reply system to the command line tool.  Messages are now sent
  from the server back to the command line tool to indicate the result
  of running the command.

- Added !include tag support to the yaml loader which reads the
  configuration file to allow the file to be split into multiple
  files ([Issue #11][I11]).

- Added linking command to put a modem/device into linking mode without
  touching it.  This lets a new device be added purely through software
  commands ([Issue #7][I7]).

- Updated the modem db delete commands so that specific records can be
  removed.  Removed the modem only db_delete command and replaced it with
  db_del_ctrl_of and db_del_resp_of just like the devices.

- Low level MQTT commands now accept "nice" names from the config file for
  all inputs including the topic.  "modem" is the nice name for the PLM modem.

- Added support for simulating button presses on devices to trigger device
  scenes ([Issue #9][I9]).

- Added support for triggering virtual scenes defined on the modem.
  ([Issue #24][I24]).

- Added support for creating multi-group controller/responder links to
  allow linking between different buttons on multi-button devices.
  ([Issue #20][I20]).


### Fixes
- [Issue #21][I21]: Fixed incorrect device database entries being created
  on the last record of the database.


## [0.5.2] - 2017-12-22

### Fixes
- [Issue #16][I16]: Python3.4 doesn't allow circular imports


## [0.5.1] - 2017-12-07

### Fixes
- [Issue #3][I3]: Dimmer on/off topic using wrong template from config file


## [0.5.0] - 2017-12-06

- Initial release



[I3]: https://github.com/TD22057/insteon-mqtt/issues/3
[I4]: https://github.com/TD22057/insteon-mqtt/issues/4
[I5]: https://github.com/TD22057/insteon-mqtt/issues/5
[I6]: https://github.com/TD22057/insteon-mqtt/issues/6
[I7]: https://github.com/TD22057/insteon-mqtt/issues/7
[I8]: https://github.com/TD22057/insteon-mqtt/issues/8
[I9]: https://github.com/TD22057/insteon-mqtt/issues/9
[I11]: https://github.com/TD22057/insteon-mqtt/issues/11
[I12]: https://github.com/TD22057/insteon-mqtt/issues/12
[I13]: https://github.com/TD22057/insteon-mqtt/issues/13
[I16]: https://github.com/TD22057/insteon-mqtt/issues/16
[I17]: https://github.com/TD22057/insteon-mqtt/issues/17
[I18]: https://github.com/TD22057/insteon-mqtt/issues/18
[I20]: https://github.com/TD22057/insteon-mqtt/issues/20
[I21]: https://github.com/TD22057/insteon-mqtt/issues/21
[I24]: https://github.com/TD22057/insteon-mqtt/issues/24
[I27]: https://github.com/TD22057/insteon-mqtt/issues/27
[I28]: https://github.com/TD22057/insteon-mqtt/issues/28
[I29]: https://github.com/TD22057/insteon-mqtt/issues/29
[I32]: https://github.com/TD22057/insteon-mqtt/issues/32
[I33]: https://github.com/TD22057/insteon-mqtt/issues/33
[I34]: https://github.com/TD22057/insteon-mqtt/issues/34
[I37]: https://github.com/TD22057/insteon-mqtt/issues/37
[I43]: https://github.com/TD22057/insteon-mqtt/issues/43
[I45]: https://github.com/TD22057/insteon-mqtt/issues/45
[I48]: https://github.com/TD22057/insteon-mqtt/issues/48
[I55]: https://github.com/TD22057/insteon-mqtt/issues/55
[I59]: https://github.com/TD22057/insteon-mqtt/issues/59
[I63]: https://github.com/TD22057/insteon-mqtt/issues/63
[I69]: https://github.com/TD22057/insteon-mqtt/issues/69
[I70]: https://github.com/TD22057/insteon-mqtt/issues/70
[I76]: https://github.com/TD22057/insteon-mqtt/issues/76
[I86]: https://github.com/TD22057/insteon-mqtt/issues/86
[I88]: https://github.com/TD22057/insteon-mqtt/issues/88
[I95]: https://github.com/TD22057/insteon-mqtt/issues/95
[I97]: https://github.com/TD22057/insteon-mqtt/issues/97
