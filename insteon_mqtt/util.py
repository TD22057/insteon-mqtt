#===========================================================================
#
# Misc utilities
#
#===========================================================================
import binascii
import io

#===========================================================================
def to_hex(data, num=None, space=' '):
    """Convert a byte array to a string of hex.

    Args:
       data:   (bytes) Bytes array to output.
       num:    (int) Number of bytes to output or None for all.
       space:  (str) String to space out bytes.

    Returns:
       (str) Returns a string of the printed bytes.
    """
    if num:
        data = data[:num]

    s = binascii.hexlify(data).decode()
    
    o = io.StringIO()
    for i in range(0, len( s ), 2):
        o.write(s[i])
        o.write(s[i+1])
        o.write(space)
        
    return o.getvalue()

#===========================================================================
