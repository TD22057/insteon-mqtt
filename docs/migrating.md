# Migrating to Discovery for Installations 0.8.3 and Earlier

The current design of InsteonMQTT uses a single configuration file.  Sadly
this means that when new additions are added to the configuration file, you
need to copy them from the sample configuration file into your own file.

## Arguments Against Migrating

Upgrading your config file to use the discovery platform and switching from
yaml defined entities in HomeAssistant o use the discovery platform will
require a little bit
of work.  Depending on your installation, this could take __hours of work__.
So please consider whether this is worth it for you.

### Does Not Offer New InsteonMQTT Functionality

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

### Upgrading Is Currently Time Consuming (Future releases should improve this)

The next minor release of InsteonMQTT intends to solve issues #383 and #391
This should decrease the amount of copy and pasting that you have to do.
It is up to you, __but it may be easier to wait for the next minor release__
before switching to the discovery platform.

## Arguments for Migrating

The discovery platform is a clear win for new users.

For existing users, the only real benefit, is likely to be minor tweaks and
improvements to the HomeAssistant interaction.  It is clear, that HomeAssistant
is heading away from the yaml configuration style and towards a more gui based
configuration.

# How to Migrate to the Discovery Platform

As noted, this could take some time, it isn't really something that you can
do in steps, so be sure you have enough time set aside.

1. Make a backup copy of your InsteonMQTT config.yaml file.
2. Make a backup copy of all HomeAssistant configurations that define insteon
entities.
3. Copy the discovery settings in the `mqtt` key from the config-example.yaml
file.  Specifically, the `enable_discovery`, `discovery_topic_base`, `discovery_ha_status` and `device_info_template` keys.
4. Under each of the device subkeys (e.g. `modem`, `switch`, `dimmer` ...) copy
the `discovery_entities` from the config-example.yaml into your config file.

>The above steps can be completed without affecting your installation.  The
following steps make changes that must either be completed or reverted to
enable things to work.

5. Check to see if any of your `*_payload` entries differs from the suggested
entry defined in the config-example.yaml.  The best way to do this is using a
diff tool.  If they are different, either update your `*_payload` defintion, or
amend the `discovery_entities` as necessary.  For example, if your
`state_payload` generates a json payload, the `discovery_entities` needs to be
defined to expect a json payload.
6.Remove or comment out the inston entities in your HomeAssistant
configuration.
7. Restart HomeAssistant (your front end will likely be filled with yellow triangles).
8. Make sure `enable_discovery` is set to `true` in your InsteonMQTT config.
9. Restart InsteonMQTT.
10. Using `Configuration -> Integrations` in HomeAssistant rename and adjust
the entity ID of the discovered insteon entities to match your prior
installation.  You can hover over the yellow triangles in your fron end to see
the missing Entity IDs.  Once the Entity ID has been fixed, the yellow triangle
will go away.  You can also review your old insteon entity defintions one by
one to verify that your entities have been created and are correctly identified.
11. Check the HomeAssistant log and the InsteonMQTT log for any errors.

> If you make changes to your InsteonMQTT config, you will need to restart
InsteonMQTT for them to take effect.  It seems like in some cases, you may
need to restart HomeAssistant for certain changes to take effect.
