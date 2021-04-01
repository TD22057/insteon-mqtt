# Debugging

If you run into a problem the following may help you fix it yourself:


1) __Monitor MQTT Messages__ You can monitor the devices to make sure things are working by watching MQTT messages.  With mosquitto, you can run the following to see every messages being sent in and out of the server.

  _Command Line_
   ```
   mosquitto_sub -v -t 'insteon/#'
   ```
__HomeAssistant__ If you are running Insteon-MQTT as a [HomeAssistant Addon](HA_Addon_Instructions.md) you can listen to MQTT topics inside HomeAssistant.  From the HomeAssistant web interface go to `Config -> Integrations -> MQTT -> Configure` then select `Listen to Topic` and enter the following topic `insteon/#` click `Listen` and you will see a stream of the messages posted to this topic.

2) __Review the Log Contents__ Inside your `config.yaml` file you can decide how your log is outputted and if it is saved to a file. See the `logging` section at the top of the file.  `screen` will output your log directly to StdOut while `file` will allow you to save the file to a location.  On linux you can run `tail -f insteon.log` to stream the log file live.  You can also increase the logging level to get more detail by adjusting `level`.

3) __Review Other Log Files__ Does your MQTT broker have a log file you can review?

4) __Review the Response to Your Command__ Commands entered from the command line and the WebGUI output nice human readable responses with error messages.  Commands sent via the MQTT interface will have to look to the log to see these messages (unless the advanced `session` option is used).

> See [user interfaces](user_interface.md) for help with the different interfaces

5) __Search Google__ Someone may have already solved your issue.

# Still Stuck?

When asking for help please provide:
```
1. A brief description of your issue or question.
2. The command you ran if relevent
3. The relevant portion of your config.yaml or scenes.yaml file
4. The output from your command
5. The relevant portion of your log file.
```

   ## Questions

   If you have questions, please look on the
   [Discussions](https://github.com/TD22057/insteon-mqtt/discussions) page
   to see if it has been asked and answered before.  If not, feel free to ask.



   ## Issues

   If you have found a bug, or wish to request a new feature, please look on the
   [Issues](https://github.com/TD22057/insteon-mqtt/issues) page to see if the
   issue or feature request has been already identified.  If not, feel free to
   add it.
