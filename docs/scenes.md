# Scene Management
The scenes.yaml file and the 'sync' and 'import-scenes' functions provide the
user with a way to control the links between devices on their Insteon network
from a configuration file.

## A Brief Description of Links and Scenes
An Insteon Scene is made up of a controller and one or more responders.  A
command issued from the controller simultaneously causes each of the responders
to respond in a pre-defined manner.  For example, pressing a KeypadLinc button
(the controller) causes a SwitchLinc device (the responder) to turn on.

The Scene is itself made up of a link on the controller for each responder in
the scene and a link on each responder corresponding to the controller.  If
one of these links is missing or wrong, the Scene may not work, or may work in
an odd manner.  Each device has a local database of its controller and responder
links.

We have attempted to use the terms 'link' and 'scene' in the manner described
above, but in some cases these terms may have been commingled. This is in
part because the Insteon specification is itself not very good at keeping these
terms straight.  Apologies for whatever confusion results.

## Options for Managing Scenes
### Physically
Insteon has a process by which you can manually create and delete scenes. We
won't go into detail, but generally this involves pressing and holding a button
for a certain period of time on the controller and each responder.  It may or
may not be helpful to invoke some magic incantation when doing this process.
Details about how to do this can be found in the instruction manuals that came
with each device.  What? You don't save those little scraps of paper? Well
you can also find most of the manuals here as well
[Insteon Support](https://www.insteon.com/support)

### Using the Command Line
Insteon-mqtt contains the 'db-add' and 'db-delete' commands which allow the
user to create and delete scenes from the command line. This can be helpful
defining more complex scenes using on_levels, when dealing with devices buried
in walls or behind objects (such as fanlincs), or when you don't want to get
anymore exercise walking around pressing buttons.

### Using a Scenes.yaml file
This is primarily what this document is about.  Insteon-mqtt offers the
user the ability to define scenes in a configuration file and to synchronize
the device databases on their network to match the defined configuration.
Insteon-mqtt also allows the user to define scenes using one of the two above
methods, or using some other means, and to import those scenes into a
configuration file, either for backup or to allow for modifications.

## Scenes.yaml
### Defining a Scenes.yaml File
The scenes.yaml file location has to be defined in the config.yaml file. An
example of how the definition should be written can be found in the
[config.yaml](../config.yaml) file.  The scenes.yaml file needs to be defined under
the insteon key using the scenes key. If a scenes.yaml file is not defined, the
results of 'import-scenes' cannot be saved to disk.

### The Format of the Scenes.yaml File
The scenes.yaml file has a simple structure that allows the user to quickly
define one or more controllers and one or more responders to define a scene.

A sample [scenes.yaml](../scenes.yaml) is included which describes in detail how
to define a scene in the scenes.yaml file.  You do not need to place anything
in your scenes.yaml file to use the 'import-scenes' function.  As long as the
file is defined in your config.yaml file, and the location is writable by
insteon-mqtt, a scenes.yaml file will be created by the 'import-scenes'
function.

### A Note about the Modem and Group Numbers
The modem can control devices using virtual scenes.  This can be helpful for
turning on an off a keypadlinc button with a light or for turning off a group
of lights simultaneously.  While, all modem controller entries require a group
number, you __should not__ specify one.  A group number will be added
automatically for you when the scenes file is processed.

### The 'Import-Scenes' Function
NOTE: Because the 'import-scenes' function may make direct writes to your
scenes.yaml file. It is recommended that you **backup your scenes.yaml file
before running 'import-scenes'** to be sure no data is lost.

The 'import-scenes' function will take the links defined on each device and
parse them into a scene which can be saved to the scenes.yaml file.  The
'import-scenes' function relies on the locally cached version of each device's
link database.  As such, it is recommended that you **run the 'refresh' command
on the device before running 'import-scenes'.**

The 'import-scenes' function will attempt to keep the order and all comments
in the scenes.yaml file when writing to the file.  However, because scenes
may be combined or split in the process of importing, **it is not always possible
to maintain comments and ordering in the scenes.yaml file.**

Much like other insteon-mqtt command.  The 'import-scenes' command can be run
from either the command line or from mqtt.  Help running [commands from the
command line](quick_start.md), you can also run `insteon-mqtt config.yaml
import-scenes -h` for help from the command line.  Help running [mqtt
commands](mqtt.md).  It is important to note, that by default, the command
will perform a *dry-run* and will only report the changes that would be made
unless you tell it to write the changes to disk.

### The 'Import-Scenes-All' Function
The 'import-scenes-all' function will perform the 'import-scenes' function on
all devices in the network.  The same caveats about 'import-scenes' apply to
this function as well.

In addition, the 'import-scenes-all' function can take quite a while to
complete particularly if you have a lot of devices and scenes and/or a slow
computer. For reference 85 devices on a raspberry pi takes about 20 seconds
to complete.  This may cause the command line to time out before the command
completes.  The command should continue to run and complete in the background
however, you will not see the results printed to the screen.  You can solve this
by editing the file (../insteon_mqtt/cmd_line/util.py) and changing the line at
the top from `TIME_OUT = 10` to something like `TIME_OUT = 30`.

You can run `insteon-mqtt config.yaml import-scenes-all -h` for help from the
command line.  Help running [mqtt commands](mqtt.md).

### The 'Sync' Function
The 'sync' function will alter the device's link database to match the scenes
defined in the scenes.yaml file.  This includes adding new links as well as
deleting un-defined links.  To repeat, **the 'sync' function will delete links
on the device that are not present in the scenes.yaml config file.**  By
default, the command will perform a *dry-run* and will only report the changes
that would be made unless you tell it to write the changes to the device.

The changes will only be made to the device on which this command is called.  So
if the user creates a new scene the 'sync' function needs to be called on all
controllers and responders in order for the scene to work properly.

Links created by the 'pair' or 'join' command will not be deleted or added by
the 'sync' command.

You can run `insteon-mqtt config.yaml sync -h` for help from the command line.
Help running [mqtt commands](docs/mqtt.md).

#### Unexpected Sync Changes
The prudent thing to do before performing a sync, is to perform a *dry-run*
sync and look at all of the changes that will be made.  It can be helpful to
also run the print_db command on the relevant devices to see what we know about
the current state of the device database.

Unexpected additions may be as a result of 1) devices that were not refreshed
such as battery powered devices or 2) small changes in the on_level or
ramp_rates.  Unexpected deletions may be the result of 1) duplicate entries
(the entry exists more than once on the device), 2) small changes in the
on_level or ramp_rate, 3) links from devices that are no longer present on your
network.

It is also possible that our understanding of the device database is wrong.
It is not uncommon for corrupt insteon messages to exist, in this case we may
believe that the device database is different than it actually is.  Try forcing
a refresh of the device database and running a *dry-run* sync on the device
again to see if the changes are still necessary.

### The 'Sync-All' Function
The 'sync-all' function will perform the 'sync' function on all devices in the
network.  The same caveats about 'sync' apply to this function as well.

You can run `insteon-mqtt config.yaml sync-all -h` for help from the command
line. Help running [mqtt commands](docs/mqtt.md).
