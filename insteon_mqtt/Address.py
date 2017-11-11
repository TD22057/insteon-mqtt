#===========================================================================
#
# Address parser
#
#===========================================================================
import binascii


class Address:
    #-----------------------------------------------------------------------
    @staticmethod
    def from_bytes(raw, offset=0):
        return Address(raw[0+offset], raw[1+offset], raw[2+offset])

    #-----------------------------------------------------------------------
    @staticmethod
    def from_json(data):
        return Address(data)

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
            id1, id2, id3 = self._addr1_to_ids(addr)

        # Input is split into 3 parts
        else:
            id1, id2, id3 = self._addr3_to_ids(addr, addr2, addr3)

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
    def to_bytes(self):
        return self.bytes

    #-----------------------------------------------------------------------
    def to_json(self):
        return self.hex

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
    def _addr1_to_ids(self, addr):
        if isinstance(addr, Address):
            return addr.ids

        elif isinstance(addr, str):
            # Handles 'AABBCC' 'AA.BB.CC' 'AA:BB:CC' 'AA BB CC'
            s = addr.replace(".","").replace(":","").replace(" ","").strip()
            id = int(s, 16)
        elif isinstance(addr, int):
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
        return (id1, id2, id3)

    #-----------------------------------------------------------------------
    def _addr3_to_ids(self, a1, a2, a3):
        id1 = int(a1) if not isinstance(a1, str) else int(a1, 16)
        id2 = int(a2) if not isinstance(a2, str) else int(a2, 16)
        id3 = int(a3) if not isinstance(a3, str) else int(a3, 16)

        if id1 > 255 or id2 > 255 or id3 > 255:
            msg = "Error trying to parse an Insteon a1ess.  The input " \
                  "integer values must be in the range 0->255 (0x00-" \
                  "0xFF).  Inputs: %s, %s, %s" % (a1, a2, a3)
            raise Exception(msg)

        return (id1, id2, id3)
    
    #-----------------------------------------------------------------------
