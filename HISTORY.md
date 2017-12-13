# Revision Change History

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

- Added reply system to the command line tool.  Messages are now sent
  from the server back to the command line tool to indicate the result
  of running the command.


## [0.5.1] - 2017-12-07

### Fixes
- [Issue #3][I3]: Dimmer on/off topic using wrong template from config file


## [0.5.0] - 2017-12-06

- Initial release



[I3]: https://github.com/TD22057/insteon-mqtt/issues/3
[I4]: https://github.com/TD22057/insteon-mqtt/issues/4
[I5]: https://github.com/TD22057/insteon-mqtt/issues/5
[I6]: https://github.com/TD22057/insteon-mqtt/issues/6
[I8]: https://github.com/TD22057/insteon-mqtt/issues/8
