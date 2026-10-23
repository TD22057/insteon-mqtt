## Testing Unreleased Versions in Home Assistant Supervisor
The Home Assistant Supervisor system makes most things pretty simple.  Testing development releases or your own code fixes is mildly more difficult.  The following instructions should help.

1. Uninstall the Insteon-MQTT app.  Your config files for the repository installed app are saved in `/config/` (which can be found at '/addon_configs/83fc19e1_insteon-mqtt/' within the VSCode or SSH app).  If you install the app locally, as described below, the configs for the locally installed app will be at:
`/addon_configs/local_insteon-mqtt/` within the VSCode or SSH app).
2. SSH into Home Assistant using the SSH app
3. cd to `/addons`
4. run `git clone https://github.com/TD22057/insteon-mqtt.git`  You can replace the repository with your own if you like.
5. cd `insteon-mqtt`
6. Use git to checkout the branch you desire.
7. When you are ready to install on Home Assistant you will have to do the following:
- edit `config.json` 
- remove the entire line that reads: `"image": "td22057/{arch}-insteon-mqtt",`
- edit the line that reads: `"version": "0.8.1",` to be something sensible, I use dates so: `"version": "2021.03.23.0",`
8. You may have to use `git stash` and `git pop` when pulling in changes, particularly after a release has occured.  This is because both branches will have changed the version line.
9. Go back into your Home Assistant instance and go to `Settings -> Apps -> Install app`
10. In the menu on the top right click `Reload`
11. You should now see the Insteon-MQTT app listed under `Local apps`, install that, it may take a few minutes to compile locally.
12. You will have to copy your InsteonMQTT `config.yaml` file to the local config directory (which can be found at '/addon_configs/local_insteon-mqtt/' within the VSCode or SSH app)
13. In the future to update your local version, you have to edit the `config.json` to trigger a new release, then run the `Reload` command in the store to see the new version.

