#===========================================================================
#
# Address parser
#
#===========================================================================
import binascii


class Address:
    #-----------------------------------------------------------------------
    @staticmethod
    def read(raw, offset=0):
        return Address(raw[0+offset], raw[1+offset], raw[2+offset])

    #-----------------------------------------------------------------------
    def __init__(self, addr, addr2=None, addr3=None):
        if (addr is None or
            (addr is not None and addr2 is not None and addr3 is None) or
            (addr is not None and addr2 is None and addr3 is not None)):
            msg = "Error trying to parse an Insteon address.  The input " \
                  "can be a single integer, string, or 3 bytes or " \
                  "strings.  Inputs: %s, %s, %s" % (addr,addr2,addr3)
            raise Exception(msg)

        # First input has all 3 byte values.
        if addr2 is None:
            # Copy constructor
            if isinstance(addr, Address):
                self.ids = addr.ids[:]
                self.id = addr.id
                self.bytes = addr.bytes
                self.hex = addr.hex
                return

            elif isinstance(addr, str):
                # Handles 'AABBCC' 'AA.BB.CC' 'AA:BB:CC' 'AA BB CC'
                s = addr.replace(".","").replace(":","").replace(" ","").strip()
                id = int(s, 16)
            elif isistance(addr, int):
                id = addr
            else:
                msg = "Error trying to parse an Insteon address.  The input " \
                      "address must be an integer or string: %s, %s, %s," % \
                      (addr,addr2,addr3)
                raise Exception(msg)

            if id < 0 or id > 0xFFFFFF:
                msg = "Error trying to parse an Insteon address.  The input " \
                      "address must in the range 0 >= %s <= %s:  Input: " \
                      % (id, 0xFFFFFF)
                raise Exception(msg)

            id1 = id >> 16 & 0xFF
            id2 = id >> 8 & 0xFF
            id3 = id & 0xFF

        # Input is split into 3 parts
        else:
            id1 = int(addr) if not isinstance(addr, str) else int(addr, 16)
            id2 = int(addr2) if not isinstance(addr2, str) else int(addr2, 16)
            id3 = int(addr3) if not isinstance(addr3, str) else int(addr3, 16)

            if id1 > 255 or id2 > 255 or id3 > 255:
                msg = "Error trying to parse an Insteon address.  The input " \
                      "integer values must be in the range 0->255 (0x00-" \
                      "0xFF).  Inputs: %s, %s, %s" % (addr,addr2,addr3)
                raise Exception(msg)


        # Store the 3 integer address ID's
        self.ids = [id1, id2, id3]

        # Convert the 3 integer values to a single integer ID to use.
        self.id = (id1 << 16) | (id2 << 8) | id3

        # Create the byte sequence for the address.
        self.bytes = bytes(self.ids)

        # And a nicely formatted hex string output.
        s = binascii.hexlify(self.bytes).decode().upper()
        self.hex = s[0:2] + "." + s[2:4] + "." + s[4:6]

    #-----------------------------------------------------------------------
    def raw(self):
        return self.bytes

    #-----------------------------------------------------------------------
    def __hash__(self):
        return self.id.__hash__

    #-----------------------------------------------------------------------
    def __eq__(self, rhs):
        return self.id == rhs.id

    #-----------------------------------------------------------------------
    def __lt__(self, rhs):
        return self.id < rhs.id

    #-----------------------------------------------------------------------
    def __str__(self):
        return self.hex

    #-----------------------------------------------------------------------
