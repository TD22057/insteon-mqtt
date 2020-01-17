# Revision Change History

## [0.6.9]

### Additions
- Added a catalog of known device category and sub-category information.  Just
  used for display in the get-model command for now.  (thanks @mooshee)

- Added an optional reason string to the state change reporting payloads and
  as an optional input for input commands.  This allows for automations to
  change behavior based on why something changed. ([Issue #138][I138])

- Added KeypadLinc low level set_flags commands to modify: load (de)attached,
  button follow masks, button off masks, non-toggle buttons.  (thanks
  @jrevans).

- Added KeypadLinc support for turning of the backlight completely (thanks
  @jrevans).

### Fixes
- Fixed bug in message emits for battery sensors. ([Issue #157][I157])

- Fixed bug in thermostat not reporting humidity changes ([Issue #160][I160])

- Updated hassio config file to include the required arch listing.
  ([Issue #139][I139])

- Added docker builds for hassio from my repo (td22057) ([Issue #148][I148])

- Fixed bug in motion sensor replies to a model info request
  ([Issue #163][I163]).

- Fixed bug in thermostat ambient temperature calculation ([Issue #142][I142])
  (thanks @krkeegan).

- Fixed bug in KeypadLinc, FanLinc, and Outlet for non-group 1 links
  ([Issue #159][I159]) (thanks @chris153002).


## [0.6.8]

### Fixes
- Fixed incorrect handling of FanLinc speed change ([Issue #126][I126])

- Fixed incorrect exception log statement in Protocol ([Issue #132][I132])

- Fixed incorrect scene names in the config loader for IOLinc, Outlet, and
  Switch.  This prevented customizing the MQTT scene topic and payload for
  those devices ([Issue #130][I130])

- Fixed incorrect set-backlight command parsing ([Issue #136][I136])


## [0.6.7]

### Fixes
- Fixed incorrect Leak signal naming ([Issue #120][I120])


## [0.6.6]

### Fixes
- Fixed incorrect Switch.set() calling sequence. ([Issue #119][I119])


## [0.6.5]

### Additions
- Initial support for Insteon thermostats has been added (thanks @krkeegan).

- Support for fast on and off commands and reporting has been added.  The
  on/off mode (normal, fast, instant) is now a command input as well as an
  output flag in the state templates.  This allows double-clicking of
  switches to be used in automation triggers (thanks @NickWaterton).
  ([Issue #66][I66]).

- Added support for manual mode state reporting (holding buttons down).
  Supported by dimmer, keypadlinc, remote, and switch (thanks
  @NickWaterton). ([Issue #104][I104]).

- New command 'get_model' added to the command line tool to retrieve and save
  the Insteon device cat, sub_cat, and firmware revision (thanks @krkeegan).
  ([Issue #55][I55]).

- New command 'join' added to the command line tool to perform a two-way
  pairing and refresh to link a device to the modem.  This combines the
  previous linknig and pair command into a single command (thanks @krkeegan).
  ([Issue #97][I97]).

- New improved NAK error response codes makes it easier to understand errors
  when the devices can't communicate (thanks @krkeegan).  ([Issue #95][I95]).

- Added a new command line input (get-devices) to get a list of the curren
  Insteon devices in JSON format.  ([Issue #84][I84]).

- Added a new command line input to factory reset the modem.

### Fixes
- Added better messages when the pair command fails because the modem db
  is out of date ([Issue #69][I69]).

- Updated docs and example config file because of breaking HomeAssistant
  MQTT light change for dimmers ([Issue #88][I88]).

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
[I66]: https://github.com/TD22057/insteon-mqtt/issues/66
[I69]: https://github.com/TD22057/insteon-mqtt/issues/69
[I70]: https://github.com/TD22057/insteon-mqtt/issues/70
[I76]: https://github.com/TD22057/insteon-mqtt/issues/76
[I84]: https://github.com/TD22057/insteon-mqtt/issues/84
[I86]: https://github.com/TD22057/insteon-mqtt/issues/86
[I88]: https://github.com/TD22057/insteon-mqtt/issues/88
[I95]: https://github.com/TD22057/insteon-mqtt/issues/95
[I97]: https://github.com/TD22057/insteon-mqtt/issues/97
[I104]: https://github.com/TD22057/insteon-mqtt/issues/104
[I119]: https://github.com/TD22057/insteon-mqtt/issues/119
[I120]: https://github.com/TD22057/insteon-mqtt/issues/120
[I126]: https://github.com/TD22057/insteon-mqtt/issues/126
[I130]: https://github.com/TD22057/insteon-mqtt/issues/130
[I132]: https://github.com/TD22057/insteon-mqtt/issues/132
[I136]: https://github.com/TD22057/insteon-mqtt/issues/136
[I138]: https://github.com/TD22057/insteon-mqtt/issues/138
[I139]: https://github.com/TD22057/insteon-mqtt/issues/139
[I142]: https://github.com/TD22057/insteon-mqtt/issues/142
[I148]: https://github.com/TD22057/insteon-mqtt/issues/148
[I157]: https://github.com/TD22057/insteon-mqtt/issues/157
[I159]: https://github.com/TD22057/insteon-mqtt/issues/159
[I160]: https://github.com/TD22057/insteon-mqtt/issues/160
[I163]: https://github.com/TD22057/insteon-mqtt/issues/163
