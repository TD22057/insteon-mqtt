import sys
import serial
import time
import binascii
from io import StringIO

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

import time
def go( dt=0.1 level=0xFF ):
    t0 = time.time()
    cmdSw1 = bytes( [ 0x02, 0x62, 0x48, 0x3d, 0x46, 0x00, 0x11, level ] )
    ack1 = bytes( [ 0x02, 0x62, 0x48, 0x3d, 0x46, 0x00, 0x11, level, 0x06 ] )

    cmdSw2 = bytes( [ 0x02, 0x62, 0x48, 0xb0, 0xad, 0x00, 0x11, level ] )
    ack2 = bytes( [ 0x02, 0x62, 0x48, 0xb0, 0xad, 0x00, 0x11, level, 0x06 ] )

    cmdSw3 = bytes( [ 0x02, 0x62, 0x3a, 0x29, 0x84, 0x00, 0x11, level ] )
    ack3 = bytes( [ 0x02, 0x62, 0x3a, 0x29, 0x84, 0x00, 0x11, level, 0x06 ] )

    port.write( cmdSw1 )
    x = bytearray()
    while True:
        idx = x.find(ack1)
        if idx != -1:
            x = x[idx+len(ack1):]
            print("READ ACK 1")
            break

        while not port.inWaiting():
            time.sleep(0.001)

        x.extend( port.read(1024) )
        print(tohex(x))

    print("BUF %d: %s" % ( len(x), tohex(x)))
    time.sleep(dt)

    port.write( cmdSw2 )
    while True:
        idx = x.find(ack2)
        if idx != -1:
            x = x[idx+len(ack2):]
            print("READ ACK 2")
            break

        while not port.inWaiting():
            time.sleep(0.001)
        x.extend(port.read(1024))
        print(tohex(x))

    print("Read %d: %s" % ( len(x), tohex(x)))
    time.sleep(dt)

    port.write( cmdSw3 )
    while True:
        idx = x.find(ack3)
        if idx != -1:
            x = x[idx+len(ack3):]
            print("READ ACK 3")
            break

        while not port.inWaiting():
            time.sleep(0.001)
        x.extend(port.read(1024))
        print(tohex(x))
    print("Read %d: %s" % ( len(x), tohex(x)))
    t1 = time.time()
    print( "Elapsed:",t1-t0)
