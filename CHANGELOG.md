# Revision Change History

## [0.7.5]

This is another significant update that both improves the user experience,
adds a number of features, and improves the performance and reliability of
the program.

### Additions

- Support for using an Insteon Hub as a modem.  It comes with some caveats
  but it works well, please see
  [Hub Instructions](https://github.com/TD22057/insteon-mqtt/blob/dev/docs/hub.md)
  ([PR 201][P201])

- Significantly improved Home Assistant Add-on installation!  
  [Instructions](docs/HA_Addon_Instructions.md) Includes update notifications,
  nicer icons, and better integration into Home Assistant. [PR 290][P290]

- A new Web Command Line Interface for Home Assistant Installations.  No more
  entering commands via MQTT topics and payloads.  [PR 238][P238]

- More pyTests, up to 76% coverage now. ([PR 262][P262] & [PR 268][P268])

- Significant improvement to the Modem database handling.  There is no longer
  a requirement to perform the command `refresh modem` for anything with the
  exception, that if you want to use `sync` to delete extra links off the
  modem, you will need to perform a `refresh` so that the extraneous links
  can be identified.  Commands will no longer fail because the modem database
  is out of date. ([PR 279][P279])

- Enable querying the battery on 2842 & 2844 Motion sensors.  Helpful if using
  battery chemistry that varies from the OEM batteries.  Voltage will be
  queried no more frequently than every 4 days.
  ([PR 282][P282] & [PR 288][P288])

- Better handling of local device on_levels.  If known, on_level is now
  accurately reported when the device turns on.  Local on_level is retrieved
  with get_flags or set with set_flags.  (thanks @tstabrawa)([PR 285][P285])

### Fixes

- Allow for used last entries in DB.  Improve compatibility with devices
  setup by ISY.  ([PR 255][P255])

- Improved message handling and processing of Pre_NAK messages.
  ([PR 236][P236])

- Don't treat broadcast messages from different groups as duplicate.  Fixes
  a bug where sequential presses of a button on a keypadlinc may not emit
  mqtt messages as they should.  (thanks @tstabrawa)([PR 256][P256])

- Catch and delay on PLM reporting busy. ([PR 261][P261])

- Tweak some of the logging to be more clear for users. ([PR 272][P272] &
  [PR 275][P275])

- Refactor code around Pair().  Add significant amount of unit tests.
  ([PR 277][P277])

- Improved message timing after receiving a broadcast command from a device.
  ([PR 284][P284])

- Fixed a few rare errors with the Serial interface.  (thanks @MrGibbage)
  ([I 292][I292])

## [0.7.4]

### Additions

- Major improvements to the IOLinc support.  In short all functions of the
  device should now be supported.  Including momentary modes in which the
  relay opens for a defined period of time before closing again.  Specific
  topics have been added for the relay and the sensor so they can both be
  tracked individually. ([PR 197][P197])  BREAKING CHANGE - the scene_topic
  has been elimited, please see the notes below for replacement functionality.
  Please see notes in:
  - [config.yaml](https://github.com/TD22057/insteon-mqtt/blob/master/config.yaml) -
    specifically the IOLinc sections in both the device and mqtt sections
  - [MQTT Doc](https://github.com/TD22057/insteon-mqtt/blob/master/docs/mqtt.md) -
    note the new set_flags options for IOLinc and the IOLinc section

- A new queueing system for battery devices ([PR240][P240]):
   - Messages sent to the device will be queued until the device is awake
   - When the device sends a message, the modem will attempt to immediately
     send the oldest outgoing message.  This only works for some devices.
   - Added an 'awake' command, to identify when a battery device has been
     manually awaken via holding the set button.  This will cause all queued
     and future messages to be sent to the device for up to three minutes

- Added support for querying the battery on a mini-remote.  The battery state
  will be automatically queried when the device wakes up if is has been 4 days
  since the last battery check and will emit messages on the battery
  topic. ([PR 244][P244])

- Added support for Smartenit EZIO4O 4 relay output module (thanks @embak)
  ([PR 219][P219])

- Device names are now printed when printing the database.  This makes reading
  the database output much easier.  ([PR 239][P239])

- Added ability to set the default ramp rate of a dimmer using the ramp_rate
  flag.  (thanks @jordanrounds)([PR 235][P235])

### Fixes

- Major fixes to a number of bugs in the Scenes management functions.
  (thanks @tstabrawa)([PR 234][P234])

- Database delta is updated on database writes.  This eliminates a number of
  unnecessary refresh requirements, particularly around pairing.  
  ([PR 248][P248])

- Minor fix to the calculation of hops on resent messages.  ([PR 259][P259])

## [0.7.3]

Fixing a number of small bugs in preparation for upcoming releases which
will add new features.

### Additions

- Added MQTT broker ID optional config input to allow the user to input the
  MQTT broker ID the client will use (thanks @kpfleming) ([PR #220][P220])

### Fixes

- Increase timeout for DB Refresh and allow retry for initial request.
  ([PR #237][P237])

- Detect disconnections during poll() calls (thanks @kpfleming) ([PR 227][P227])

- Modem Responder Group from Thermostat Should be 0x01 ([PR #198][P198])
  ([Issue 154][I154])

- Fixed device db find command to check the local group so multiple responsders
  can be created. ([Issue #181][I181])

- Fixed a bug in the modem database class when removing an entry (thanks
  @krkeegan) ([PR#196][P196])

- Changed the MQTT Remote to never mark messages for retain so the broker
  doesn't get out of sync with the device. ([Issue #I210][I210])


## [0.7.2]

### Fixes

- Fixed an issue causing 100% cpu usage introduced in the scene sync code.
  ([Issue #195)[I195])


## [0.7.1]

### Fixes

- Fixed a coding bug when running sync-all ([Issue #192][I192])
  (thanks @krkeegan)

- Fixed a coding bug when running sync on the modem ([Issue #193][I193])
  (thanks @krkeegan)


## [0.7.0]

### Additions
- Thanks to @krkeegan, scene management and syncing are now supported.  This
  allows you to define all of your Insteon scenes in a configuration file and
  have the system sync your devices to that file. ([Issue #25][I25],
  [Issue #179][I179])

- Enable software control of motion sensor flags ([Issue #184][I184])
  (thanks @krkeegan)

- Added support for single button remotes ([Issue #185][I185])
  (thanks @krkeegan)

- Added an option to skip battery devices when doing a refresh and a new
  command to get the engine version (for older I1 devices) ([Issue #189][I189])
  (thanks @krkeegan)


### Fixes
- Fixed an error in the Thermostat MQTT code preventing user specified topics
  ([Issue #182][I182]) (thanks @krkeegan)

- Fixed issues with handling housekeeping messages sent to the model during
  a scene command.  ([Issue #183][I183]) (thanks @krkeegan)


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
[I25]: https://github.com/TD22057/insteon-mqtt/issues/25
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
[I179]: https://github.com/TD22057/insteon-mqtt/issues/179
[I182]: https://github.com/TD22057/insteon-mqtt/issues/182
[I183]: https://github.com/TD22057/insteon-mqtt/issues/183
[I184]: https://github.com/TD22057/insteon-mqtt/issues/184
[I185]: https://github.com/TD22057/insteon-mqtt/issues/185
[I189]: https://github.com/TD22057/insteon-mqtt/issues/189
[I192]: https://github.com/TD22057/insteon-mqtt/issues/192
[I193]: https://github.com/TD22057/insteon-mqtt/issues/193
[I195]: https://github.com/TD22057/insteon-mqtt/issues/195
[P196]: https://github.com/TD22057/insteon-mqtt/pull/196
[I210]: https://github.com/TD22057/insteon-mqtt/issues/210
[P220]: https://github.com/TD22057/insteon-mqtt/pull/220
[I181]: https://github.com/TD22057/insteon-mqtt/issues/181
[I154]: https://github.com/TD22057/insteon-mqtt/issues/154
[P227]: https://github.com/TD22057/insteon-mqtt/pull/227
[P237]: https://github.com/TD22057/insteon-mqtt/pull/227
[P197]: https://github.com/TD22057/insteon-mqtt/pull/197
[P240]: https://github.com/TD22057/insteon-mqtt/pull/240
[P248]: https://github.com/TD22057/insteon-mqtt/pull/248
[P219]: https://github.com/TD22057/insteon-mqtt/pull/219
[P239]: https://github.com/TD22057/insteon-mqtt/pull/239
[P244]: https://github.com/TD22057/insteon-mqtt/pull/244
[P235]: https://github.com/TD22057/insteon-mqtt/pull/235
[P259]: https://github.com/TD22057/insteon-mqtt/pull/259
[P234]: https://github.com/TD22057/insteon-mqtt/pull/234
[P236]: https://github.com/TD22057/insteon-mqtt/pull/236
[P255]: https://github.com/TD22057/insteon-mqtt/pull/255
[P256]: https://github.com/TD22057/insteon-mqtt/pull/256
[P261]: https://github.com/TD22057/insteon-mqtt/pull/261
[P262]: https://github.com/TD22057/insteon-mqtt/pull/262
[P268]: https://github.com/TD22057/insteon-mqtt/pull/268
[P272]: https://github.com/TD22057/insteon-mqtt/pull/272
[P201]: https://github.com/TD22057/insteon-mqtt/pull/201
[P275]: https://github.com/TD22057/insteon-mqtt/pull/275
[P277]: https://github.com/TD22057/insteon-mqtt/pull/277
[P279]: https://github.com/TD22057/insteon-mqtt/pull/279
[P282]: https://github.com/TD22057/insteon-mqtt/pull/282
[P288]: https://github.com/TD22057/insteon-mqtt/pull/288
[P284]: https://github.com/TD22057/insteon-mqtt/pull/284
[P290]: https://github.com/TD22057/insteon-mqtt/pull/290
[P238]: https://github.com/TD22057/insteon-mqtt/pull/238
[I292]: https://github.com/TD22057/insteon-mqtt/issues/292
[P285]: https://github.com/TD22057/insteon-mqtt/pull/285
