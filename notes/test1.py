import serial
import time
import binascii
from io import StringIO
import insteon_mqtt as IM

# see dev guide p106 for examples and all link stuff
# SA commands see p165
#
# 0x02 0x15 message = not ready - resend command
# 0x02 [prev mesg] 0x06 = ACK

# NOTE: for switch->device, the switch will send a command to the
# modem, but we don't see the command sent to the device.  And the
# device doesn't send an update to the modem when it does something
# from a command.  So we have to know that the switch is linked to the
# device.
#
# My guess is this is why all the code gets the all link database so
# that this linkage can be known.

port = serial.Serial( port="/dev/insteon",
                      baudrate=19200,
                      parity=serial.PARITY_NONE,
                      stopbits=serial.STOPBITS_ONE,
                      bytesize=serial.EIGHTBITS,
                      timeout=0 )
while not port.is_open:
    print( "port not open?" )
    time.sleep( 1 )

print( "port variable defined and ready" )

def tohex( data ):
    s = binascii.hexlify(data).decode()
    o = StringIO()
    for i in range( 0, len( s ), 2 ):
        o.write( s[i] )
        o.write( s[i+1] )
        o.write( ' ' )
    return o.getvalue()

def read():
    if port.inWaiting():
        data = port.read(1024)
        print("Read %d: %s" % ( len(data), tohex(data)))
        return data
    print("No bytes to read")
    return None

dimUpBeg = bytes( [ 0x02, 0x62, 0x00, 0x00, 0x01, 0x3f, 0x17, 0x01 ] )
dimUpEnd = bytes( [ 0x02, 0x62, 0x00, 0x00, 0x01, 0x3f, 0x18, 0x01 ] )


# TURN ON
msg1 = bytes( [
    0x02, 0x62,  # header
    0x3a, 0x29, 0x84,  # address
    0x00, # flags
    0x11, 0xFF,  # turn on level 255
    ] )
# Sent: 02 62 31 29 84 00 11 ff
# Recv: 02 62 3a 29 84 00 11 ff 06 02 50 3a 29 84 44 85 11 20 11 ff
#
# 02 62 3a 29 84 00 11 ff 06
# repeat back of same message with 06 ACK byte at end. 0x15 = error
#
# 02 50 3a 29 84 44 85 11 20 11 ff
#   50 = PLM -> host standard message (9 bytes+ack)
#   3a 29 84 = from address
#   44 85 11 = PLM address
#   20 msg flags (direct ack)
#   11 light on
#   ff level 255


# TURN OFF
msg2 = bytes( [
    0x02, 0x62,  # header
    0x3a, 0x29, 0x84,  # address
    0x00, # flags
    0x13, 0x00,  # turn off
    ] )
rtn2 = b'\x02b:)\x84\x00\x13\x00\x06\x02P:)\x84D\x85\x11 \x13\x00'
# Sent: 02 62 31 29 84 00 13 00
# Recv: 02 62 3a 29 84 00 13 00 06 02 50 3a 29 84 44 85 11 20 13 00
#
# 02 62 3a 29 84 00 13 00 06
# repeat back of same message with 06 ACK byte at end. 0x15 = error
#
# 02 50 3a 29 84 44 85 11 20 13 00
#   50 = PLM -> host standard message (9 bytes+ack)
#   3a 29 84 = from address
#   44 85 11 = PLM address
#   20 msg flags (direct ack)
#   13 light off
#   00 level 0 [unused]


statusMsg = bytes( [
    0x02, 0x62, # header
    0x3a, 0x29, 0x84, # light address
    0x00,  # flags
    0x19, 0x00,  # status request, ack w/ brightness.
    ] )
mdoemStatus = bytes( [
    0x02, 0x62, # header
    0x44, 0x85, 0x11, # light address
    0x00,  # flags
    0x19, 0x00,  # status request, ack w/ brightness.
    ] )

# Sent: 02 62 3a 29 84 00 19 00
# Recv: 02 62 3a 29 84 00 19 00 06 02 50 3a 29 84 44 85 11 20 00 00
#
# 02 62 3a 29 84 00 19 00 06
# repeat back of same message with 06 ACK byte at end. 0x15 = error
#
# 02 50
# 3a 29 84  = light address
# 44 85 11  = plm address
# 20 = direct ack
# 00 = all link delta
# 00 = current light level


#==================================
# 20 msg flags
# bin((0x20 | 0b11100000) > 5 )
# '0b1'
# which is 0b001 == DIRECT_ACK
# if 0b101, then it's NAK and a problem occurred. (DIRECT_NAK)

#==================================
# Turn light on manually:
# 02 50 3a 29 84 00 00 01 cf 11 00
# 02 50 3a 29 84 00 00 01 cf 11 00
# 02 50 3a 29 84 44 85 11 45 11 01
# 02 50 3a 29 84 11 01 01 cf 06 00
#
# 1) 02 50 3a 29 84 00 00 01 cf 11 00
#   3a 29 84 = light address
#   00 00 01 = all link group 0x01 (first two bytes always 0 in this case)
#   cf = flags 110 = all link broadcast (110), max hops
#   11 = SA command
#   00 = unused
#
# 3) 02 50 3a 29 84 44 85 11 45 11 01
#   3a 29 84 = light address
#   84 44 85 = PLM address
#   45 = flags b010 = all link clean up
#   11 = SA command: (p165) light on (or all-link recall 0)
#   01 = group #
#
# 4) 02 50 3a 29 84 11 01 01 cf 06 00
#   3a 29 84 = light address
#   11 01 01 = think last byte is group number
#   cf = flags 011 = all link cleanup ACK
#   06 = cleanup success = device got acks from all items
#   00 = unused
#
# NOTE: each device checks it's address against the all-link database
# to see if it's the sent group #.  If it is, it runs the command.
#
#==================================
# Turn light off manually:
# 02 50 3a 29 84 00 00 01 cf 13 00
# 02 50 3a 29 84 00 00 01 cf 13 00
# 02 50 3a 29 84 44 85 11 45 13 01
# 02 50 3a 29 84 13 01 01 cf 06 00
#
# 02 50 3a 29 84 00 00 01 cf 13 00
#   00 00 01 = all link group 0x01 (first two bytes always 0 in this case)
#   cf = flags 110 = all link broadcast (110), max hops
#   13 = SA command (p165) light off
#   00 = unused
# Others are the same as on - just w/ 0x13 light off as command

#==================================
# turn light on manually:
#
# hold down to dim for a couple of seconds
# 02 50 3a 29 84 00 00 01 cf 17 00
# 02 50 3a 29 84 00 00 01 cf 18 00
#
# 1) 02 50 3a 29 84 00 00 01 cf 17 00
# 00 00 01
# cf
# 17 = start manual change
# 00 = direction down (p139)
#
# 2) 02 50 3a 29 84 00 00 01 cf 18 00
# 00 00 01
# cf
# 18 = stop manual change
# 00 = not used

#==================================
# light on after holding down then status request:
# 02 62 3a 29 84 00 19 00 06
# 02 50 3a 29 84 44 85 11 20 00 fe
# 20 = ack
# 00
# fe = current light level

#==================================
# Hold dimmer switch up to certain level
# 02 50 48 3d 46 00 00 01 cf 17 00
# 02 50 48 3d 46 00 00 01 cf 18 00


s = """
Light notes:

for values initiated by Light class:
   send set command
   recv echo back w/ ack == no error in command
   recv reply back == confirm level change

for values triggered manually:
   recv manual mode change started, stopped
   send status request
   recv status back == confirm level change
"""

status2 = bytes( [
    0x02, 0x62, # header
    0x21, 0xd6, 0xd9, # motion sensor
    0x00,  # flags
    0x19, 0x00,  # status request, ack w/ brightness.
    ] )
# NOTE: sending status to motion sensor when it's not on does nothing.
# it must be active to get a status request.

#==================================
# Motion sensor tripping
# 02 50 21 d6 d9 00 00 01 cb 11 01
# 02 50 21 d6 d9 00 00 01 cf 11 01
#
# 02 50
# 21 d6 d9 = sensor address
# 00 00 01 = all link group 0x01
# cb = flags 110 = all link broadcast
# 11 = SA command (on)
# 01 = ?
#
# 02 50
# 21 d6 d9 = sensor address
# 00 00 01 = all link group 0x01
# cf = flags 110 = all link broadcast
# 11 = SA command (on)
# 01  = ?
#
#---------
# After sensor is hidden for awhile
# 02 50 21 d6 d9 44 85 11 45 11 01
# 02 50 21 d6 d9 11 03 01 cf 06 02
# 02 50 21 d6 d9 11 03 01 cf 06 02
#
# 02 50
# 21 d6 d9 = sensor address
# 44 85 11 = modem address
# 45 = flags b010 = all link clean up
# 11 = SA command: (p165) light on (or all-link recall 0)
# 01 = group #
#
# 02 50
# 21 d6 d9
# 11 03 01 = dev cat 0x11 (security), sub cat 0x03, ver 0x01
# cf = flags  110 = all link broadcast
# 06 = ??
# 02 = ??
#
#------------
# Really long after sensor hidden
# 02 50 21 d6 d9 00 00 01 cf 13 01
# 02 50 21 d6 d9 44 85 11 41 13 01
# 02 50 21 d6 d9 13 03 01 cf 06 02
# 02 50 21 d6 d9 13 03 01 cb 06 02
#
# 02 50
# 21 d6 d9 = sensor address
# 00 00 01 = all link group 0x01
# cf = flags 110 = all link broadcast
# 13 = SA command (off)
# 01 = ?
#
# 02 50
# 21 d6 d9 = sensor address
# 44 85 11 = modem address
# 41 = flags b010 = all link clean up
# 13 = CA command off
# 01 = group #
#
# 02 50
# 21 d6 d9 = sensor address
# 13 03 01 = ??
# cf = flags 110 = all link broadcast
# 06 = ??
# 02 = ??
#
# 02 50
# 21 d6 d9 = sensor address
# 13 03 01
# cb = flags 110 = all link broadcast
# 06 = ??
# 02 = ??

#--------------------------------
# product data request cmd = 0x03 0x00
# to lamplinc
#
# 02 62 3a 29 84 00 03 00 06
# 02 50 3a 29 84 44 85 11 20 03 00
#
# 02 50
# 3a 29 84
# 44 85 11
# 20
# 03
# 00
#
# cmd = 0x03 0x02 (text response)
#
# 02 62 3a 29 84 00 03 02 06
# 02 50 3a 29 84 44 85 11 20 03 02
#
# 02 50
# 3a 29 84
# 44 85 11
# 20
# 03
# 02

#=======================================================
# on/off module: 37 2d 35
# SAME as dimmer module

# remote: 3f 07 d4
# double click button on remote after pairing w/ lamp module above
# note: lots of duplicates

# ON
# 02 50 3f 07 d4 00 00 02 cf 13 00
# 02 50 3f 07 d4 00 00 02 cf 11 00
# 02 50 3f 07 d4 44 85 11 45 11 02
# 02 50 3f 07 d4 11 03 02 cf 06 01

# 02 50
# 3f 07 d4 = from address
# 00 00 02 = all link group 02
# cf = flags 110 = all link broadcast (110), max hops
# 13 light off , 11 = light on
# 00 group?
#
# 02 50
# 3f 07 d4 = from address (remote)
# 44 85 11 = modem address
# 45 = flags b010 = all link clean up
# 11 = SA command light on
# 02 = all link group

# OFF
# 02 50 3f 07 d4 00 00 02 cf 17 00
# 02 50 3f 07 d4 00 00 02 cf 18 00
# 02 50 3f 07 d4 00 00 02 cf 11 00
# 02 50 3f 07 d4 00 00 02 cf 14 00

# single tap on:
# 02 50 3f 07 d4 44 85 11 45 14 02
# 02 50 3f 07 d4 14 03 02 cf 06 01
# 02 50 3f 07 d4 00 00 02 cf 11 00

# 02 50
# 3f 07 d4
# 44 85 11
# 45 = all link clean up.
# 14 = light off or alias 2 low
# 02 = group

# then a little while later?
# 02 50 3f 07 d4 44 85 11 45 11 02
# 02 50 3f 07 d4 11 03 02 cf 06 01
# 02 50 3f 07 d4 11 03 02 cb 06 01

#=================================================================
# 3 way scene test
# 1 lamp module, 2 dimmer switches
# link all 3 both ways to modem, then link all in ON state to each other:
# dimmer->lamp:  dimmer set, turn on lamp, lamp set
# lamp->dimmer:  lamp set, turn on dimmer, dimmer set
# dimmer1->dimmer2:  dimmer1 set, turn on dimmer2, dimmer2 set
#
onMod = bytes( [
    0x02, 0x62,  # header
    0x37, 0x2d, 0x35,  # address
    0x00, # flags
    0x11, 0xFF,  # turn on level 255
    ] )
# lamp module turned on, switches did not respond.
# reply was huge number of 0x00 bytes then:
# 02 62 37 2d 35 00 11 ff 06
# 02 50 37 2d 35 44 85 11 21 11 ff
# replay + from addr + PLM addr
# 21 msg flags = direct ack
# 11 ff = on at 255
# = echo and direct ack

offMod = bytes( [
    0x02, 0x62,  # header
    0x37, 0x2d, 0x35,  # address
    0x00, # flags
    0x13, 0x00,  # turn off
    ] )
# lamp module turned off, switches did not respond
# 02 62 37 2d 35 00 13 00 06
# 02 50 37 2d 35 44 85 11 25 13 00
# = echo and direct ack

onSw = bytes( [
    0x02, 0x62,  # header
    0x48, 0x3d, 0x46,  # address
    0x00, # flags
    0x11, 0xFF,  # turn on level 255
    ] )
# switch shows on state, but lamp and other switch don't respond
# 02 62 48 3d 46 00 11 ff 06
# 02 50 48 3d 46 44 85 11 20 11 ff

offSw = bytes( [
    0x02, 0x62,  # header
    0x48, 0x3d, 0x46,  # address
    0x00, # flags
    0x13, 0x00,  # turn off
    ] )
# lamp module turned off, switches did not respond
# 02 62 48 3d 46 00 13 00 06
# 02 50 48 3d 46 44 85 11 20 13 00

# Turn lamp module on
# 02 50 37 2d 35 00 00 01 cf 11 00
# 02 50 37 2d 35 44 85 11 4a 11 01
# 02 50 37 2d 35 11 03 01 c7 06 00

# Turn lamp module off
# 02 50 37 2d 35 00 00 01 cf 13 00
# 02 50 37 2d 35 44 85 11 41 13 01
# 02 50 37 2d 35 13 03 01 cb 06 00

# Turn dimmer switch on
# 02 50 48 b0 ad 00 00 01 cf 11 00
# 02 50 48 b0 ad 44 85 11 40 11 01
# 02 50 48 b0 ad 11 03 01 cf 06 00

# Turn dimmer switch off
# 02 50 48 b0 ad 00 00 01 cf 13 00
# 02 50 48 b0 ad 44 85 11 40 13 01
# 02 50 48 b0 ad 44 85 11 45 13 01
# 02 50 48 b0 ad 13 03 01 cf 06 00

#=========================================
# smoke bridge tab test button repeatedly
# 02 50 44 a3 79 00 00 01 cf 11 80
# 00 00 01 = all link group 0x01 (first two bytes always 0 in this case)
#   cf = flags 110 = all link broadcast (110), max hops
#   11 = SA command
#   80 = unused?

# 02 50 44 a3 79 44 85 11
# 4a = all link clean up
# 11 01 = SA command
# 02 50 44 a3 79 44 85 11 45 11 01
# 02 50 44 a3 79
# 11 01 01 = dev cat 0x11, sub cat 0x01, firmware 0x01
# cf = flags 110 = all link broadcast (110), max hops
# 06 = SA command

#=========================================
# link 2 dimmers, 1 dimmer lamp module
# dimmers = 48.3d.46, 48.b0.ad
# lamp = 3a.29.84
# send:
dimUpBeg = bytes( [ 0x02,0x62,0x00,0x00,0x01,0xcf,0x17,0x01 ] )
dimUpEnd = bytes( [ 0x02,0x62,0x00,0x00,0x01,0xcf,0x18,0x00 ] )
# this starts both dimmers moving up, but not the lamp???
# read:
# 02 50 3a 29 84 00 00 01 cf 13 00
# lamp module group 01 off?
# 02 50 3a 29 84 44 85 11 4a 13 01
# 02 50 3a 29 84 13 03 01 cb 06 00
# 02 62 00 00 01 cf 17 01 06

# holding dimmer1 button up:
# 02 50 48 3d 46 00 00 01 cb 17 01
# 02 50 48 3d 46 00 00 01 cf 18 00

#=========================================
# Mash 2 scene buttons at the same time - first on then off
# Get messages mixed together.
#
# First: group broadcast msgs:
# 02 50 3a 29 84 00 00 01 cb 11 00
# 02 50 37 2d 35 00 00 01 cb 11 00
#
# Then clean up messages
# 02 50 3a 29 84 44 85 11 41 11 01
# 02 50 37 2d 35 44 85 11 4b 11 01
#
# Lost 1 broadcast for off:
# 02 50 37 2d 35 00 00 01 cb 13 00
#
# clean up:
# 02 50 37 2d 35 44 85 11 41 13 01
# 02 50 3a 29 84 44 85 11 46 13 01
#
# final:
# 02 50 3a 29 84 13 03 01 cb 06 00
# 02 50 37 2d 35 13 03 01 cb 06 00
#
# 2nd attempt:
# Lost 1 broadcast
# 02 50 3a 29 84 00 00 01 cb 11 00
#
# 02 50 3a 29 84 44 85 11 41 11 01
# 02 50 37 2d 35 44 85 11 47 11 01
#
# Lost 1 broadcast:
# 02 50 3a 29 84 00 00 01 cf 13 00
#
# got clean ups in slightly different order
# 02 50 3a 29 84 44 85 11 45 13 01
# 02 50 3a 29 84 13 03 01 cf 06 00
#
# 02 50 37 2d 35 44 85 11 41 13 01
# 02 50 37 2d 35 13 03 01 cb 06 00
#

import time
def go( level=0xFF ):
    t0 = time.time()
    cmdSw1 = bytes( [ 0x02, 0x62, 0x48, 0x3d, 0x46, 0x00, 0x11, level ] )
    cmdSw2 = bytes( [ 0x02, 0x62, 0x48, 0xb0, 0xad, 0x00, 0x11, level ] )
    cmdSw3 = bytes( [ 0x02, 0x62, 0x3a, 0x29, 0x84, 0x00, 0x11, level ] )
    port.write( cmdSw1 )
    x = bytes()
    while len(x)<20:
        while not port.inWaiting():
            time.sleep(0.001)
        x += port.read(1024)
    print("Read %d: %s" % ( len(x), tohex(x)))

    port.write( cmdSw2 )
    x = bytes()
    while len(x)<20:
        while not port.inWaiting():
            time.sleep(0.001)
        x += port.read(1024)
    print("Read %d: %s" % ( len(x), tohex(x)))

    port.write( cmdSw3 )
    x = bytes()
    while len(x)<20:
        while not port.inWaiting():
            time.sleep(0.001)
        x += port.read(1024)
    print("Read %d: %s" % ( len(x), tohex(x)))
    t1 = time.time()
    print( "Elapsed:",t1-t0)

#=======================================================
# remote: 3f 07 d4
#
# click button once (several duplicates)
# quickly:
# 02 50 3f 07 d4 00 00 02 cb 11 00
# very slowly:
# 02 50 3f 07 d4 44 85 11 45 11 02
# 02 50 3f 07 d4 11 03 02 cf 06 01
#
# 02 50
# 3f 07 d4  remote address
# 00 00 02  all link group 02
# cb        flags 110 = all link broadcast
# 11 00     command (on)
#
# click again
# quickly:
# 02 50 3f 07 d4 00 00 02 cf 13 00
# slowly:
# 02 50 3f 07 d4 44 85 11 41 13 02
# 02 50 3f 07 d4 13 03 02 cf 06 01
#
# 02 50 3f 07 d4 00 00 02 cb 11 00
# 02 50 3f 07 d4 00 00 02 cf 11 00
# 02 50 3f 07 d4 00 00 02 cf 13 00
# 02 50 3f 07 d4 00 00 02 cf 13 00

# double click button:
# 02 50 3f 07 d4 00 00 02 cf 12 00
# 02 50 3f 07 d4 00 00 02 cf 12 00
# then again:
# 02 50 3f 07 d4 00 00 02 cf 14 00


#=======================================================
# test get extended for remotelinc
get_ext = bytes( [
    0x02, 0x62,  # header
    0x3f, 0x07, 0xd4,
    0x1f, # flags - ext message.
    0x2e, 0x00,  # extended get flags
    # 14 byte extended
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0xd2
    ] )

# 02 62 3f 07 d4 1f 2e 00 00 00 00 00 00 00 00 00 00 00 00 00 00 d2 06
# 02 50
# 3f 07 d4
# 44 85 11
# 2f 2e 00
# 02 51
# 3f 07 d4
# 44 85 11
# 1b 2e 00
# 00
# 01  D2 data response
# 04  D3 awake time in seconds
# 00  D4 heartbeat interval
# 00  D5 number of heartbeat messages
# 00  D6 button trigger command
# 00  D7
# 03  D8
# b2  D9  (178/50 = 3.56)
# a6  D10  (166/50 = 3.32)
# 8f  D11  (143/150 = 2.86)
# 00  D12
# 00  D13
# d2  D14  checksum

#=======================================================
# test get flags for keypadlinc
read_op5 = bytes( [
    0x02, 0x62,
    0x3c, 0x42, 0x9b,
    0x0f,
    0x1f, 0x05 ] )
# 02 62 3c 42 9b 0f 1f 05
# 06 02 50 3c 42 9b 44 85 11 2f 1f 0d
# 0d == 00 N/A, smart hops
#       00 detach load, N/A
#       11 blinkon error, cleanupOn,
#       01 NX10Flag, TenD

detach_load = bytes( [
    0x02, 0x62,
    0x3c, 0x42, 0x9b,
    0x1f,
    0x20, 0x1b,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xc5 ] )
# 02 62 3c 42 9b 1f 20 1b 00 00 00 00 00 00 00 00 00 00 00 00 00 c5
# 06 02 50
# 3c 42 9b
# 44 85 11
# 2f   == ACK
# 20 1b
# read_op5:
# 06 02 50 3c 42 9b 44 85 11 2f 1f 2d
# 0x2d = 0b101101
# 0d == 00 N/A, smart hops
#       10 detach load, N/A
#       11 blinkon error, cleanupOn,
#       01 NX10Flag, TenD
attach_load = bytes( [
    0x02, 0x62,
    0x3c, 0x42, 0x9b,
    0x1f,
    0x20, 0x1a,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xc6 ] )

# read_op5 w/ detached_load
# 02 62 3c 42 9b 0f 1f 05 06
# 02 50 3c 42 9b 44 85 11 2f 1f 2d
# 2d = 10 11 01  == load detached (bit 6/8)
addr = IM.Address( 0x3c, 0x42, 0x9b )
kp_on1 = bytes( [
    0x02, 0x62,  # header
    0x3c, 0x42, 0x9b,  # address
    0x00, # flags
    0x11, 0xFF,  # turn on level 255
    ] )
# detach load: nothing happens
# 02 62 3c 42 9b 00 11 ff
# 06 02 50 3c 42 9b   44 85 11   20   11 ff == ACK (but nothing happened)
data = bytes( [ 0x01, 0x09, 0b00001001 ] + [0x00]*11 )
kp_on1a = IM.message.OutExtended.direct(addr,0x2e,0x00,data).to_bytes()
# DOESN"T WORK!
# 02 62 3c 42 9b 1f 2e 00 01 09 01 00 00 00 00 00 00 00 00 00 00 c7 06
# 02 50 3c 42 9b 44 85 11  2f  2e 00 == ack

kp_off1 = bytes( [
    0x02, 0x62,  # header
    0x3c, 0x42, 0x9b,  # address
    0x00, # flags
    0x13, 0x00,  # turn off
    ] )
