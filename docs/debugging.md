# Questions, Issues, and Debugging

## Self Help
This project is a hobby for everyone involved.  So unless things are rightly and truly busted, you may not get a response to your question for days to weeks.  

If you run into a problem, the fastest way to solve it is to fix it yourself. The following will help you diagnose your troubles:

#### Monitor MQTT Messages
You can monitor the devices to make sure things are working by watching MQTT messages.  With mosquitto, you can run the following to see every messages being sent in and out of the server.

  _Command Line_
   ```
   mosquitto_sub -v -t 'insteon/#'
   ```
> __HomeAssistant__ If you are running Insteon-MQTT as a [HomeAssistant Addon](HA_Addon_Instructions.md) you can listen to MQTT topics inside HomeAssistant.  From the HomeAssistant web interface go to `Config -> Integrations -> MQTT -> Configure` then select `Listen to Topic` and enter the following topic `insteon/#` click `Listen` and you will see a stream of the messages posted to this topic.

#### Review the Log Contents
Inside your `config.yaml` file you can decide how your log is outputted and if it is saved to a file. See the `logging` section at the top of the file.  `screen` will output your log directly to StdOut while `file` will allow you to save the file to a location.  On linux you can run `tail -f insteon.log` to stream the log file live.  You can also increase the logging level to get more detail by adjusting `level`.

#### Review Other Log Files
Does your MQTT broker have a log file you can review?

#### Review the Response to Your Command
Commands entered from the command line and the WebGUI output nice human readable responses with error messages.  Commands sent via the MQTT interface will have to look to the log to see these messages (unless the advanced `session` option is used).

> See [user interfaces](user_interface.md) for help with the different interfaces

#### Search The Internet
Someone may have already solved your issue.  You can search prior issues and discussions on this repository:
1. Enter your query in the search bar on the top left of this page.
2. Hit `Enter` or select `In this repository`
3. On the results page select `Code` then select `Markdown`. This will show if your answer is documented in the documentation.
4. On the results page select `Issues`, has anyone reported this issue before?
5. On the results page select `Discussions`, has anyone asked about this before?

Also try searching Google.  You may be suprised.

#### Does your problem relate to HomeAssistant?
HomeAssistant is great, but incredibly large and complicated.  Luckily, HomeAssistant provides incredible [documentation](https://www.home-assistant.io/docs/), (see also [integrations documentation](https://www.home-assistant.io/integrations/)) and its [forums](https://community.home-assistant.io/) are very active.  You can likely solve your HomeAssitant issues much faster by using the HomeAssistant community.

## Still Stuck?
When asking for help please provide:
```
1. A brief description of your issue or question.
2. The command you ran if relevent
3. The relevant portion of your config.yaml or scenes.yaml file
4. The output from your command
5. The relevant portion of your log file.
```

> Short broad statements like `This is broken` or `I can't get this to work` are not helpful.  Please provide details about what you have tried to do, what your configuration looks like and any logging information or output you have received.  


   #### Questions

   If you have questions, please look on the
   [Discussions](https://github.com/TD22057/insteon-mqtt/discussions) page
   to see if it has been asked and answered before.  If not, feel free to ask.



   #### Issues

   If you have found a bug, or wish to request a new feature, please look on the
   [Issues](https://github.com/TD22057/insteon-mqtt/issues) page to see if the
   issue or feature request has been already identified.  If not, feel free to
   add it.
