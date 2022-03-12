# Migrating to Discovery for Installations 0.8.3 and Earlier

Prior to version 1.0.0 InsteonMQTT used a single configuration file.  Starting in version 1.0.0, the base configuration settings are contained in a base configuration file that ships with InsteonMQTT.  You can view the contents of this file here: [config-base.yaml](../insteon_mqtt/data/config-base.yaml)

As described in [configuration](configuration.md), the settings in this base configuration file can be overwritten using your user configuration file.

As a result, the easiest way to upgrade is to start a new `config.yaml` file as described below.  However, before changing, consider if the Discovery Platform is worth it to you.

### Does Not In Itself Offer New InsteonMQTT Functionality

The discovery platform is a __great feature for new users__.  It allows them to
define insteon devices once and get HomeAssistant entities with zero effort.

However, if you have already put in the work to define your insteon entities
in HomeAssistant there is likely little benefit to abandoning that work. The
discovery platform does not expose any additional features or functionality
that you cannot achieve with standard yaml defined entities.

### Offers Minor Improvements to HomeAssistant Functionality

Using the Discovery Platform will give you access to the entity registery
through the `Configuration -> Integrations` page in HomeAssistant.  This allows
the user to change items using a graphical user interface, but all of the same
items can be modified using yaml defintions as well.

### May Offer Access to Future InsteonMQTT Features or Fixes via Upgrades

Starting in version 1.0.0, now that the base config file is pushed as part of each upgrade, tweaks or fixes to the templates can be sent directly to you.  Depending on your personality, this may be a good or a bad thing.

# How to Migrate to the Discovery Platform

As noted, this could take some time, it isn't really something that you can
do in steps, so be sure you have enough time set aside.

1. Move your InsteonMQTT config.yaml file to config-backup.yaml.
2. Make a backup copy of all HomeAssistant configurations that define insteon
entities.
3. Rename `config-yaml.default` to `config.yaml`.
4. Follow the insstructions [Configuration Instructions](configuration.md) copying the details of your modem, devices, and mqtt broker from your backup file.
5.Remove or comment out the insteon entities in your HomeAssistant
configuration.
6. Restart HomeAssistant (your front end will likely be filled with yellow triangles).
7. Make sure `enable_discovery` is set to `true` in your InsteonMQTT config.
8. Restart InsteonMQTT.
9. Using `Configuration -> Integrations` in HomeAssistant rename and adjust
the entity ID of the discovered insteon entities to match your prior
installation.  You can hover over the yellow triangles in your fron end to see
the missing Entity IDs.  Once the Entity ID has been fixed, the yellow triangle
will go away.  You can also review your old insteon entity defintions one by
one to verify that your entities have been created and are correctly identified.
10. Check the HomeAssistant log and the InsteonMQTT log for any errors.

> If you make changes to your InsteonMQTT config, you will need to restart
InsteonMQTT for them to take effect.  It seems like in some cases, you may
need to restart HomeAssistant for certain changes to take effect.
