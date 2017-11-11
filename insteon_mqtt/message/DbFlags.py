#===========================================================================
#
# Message flag class
#
#===========================================================================
import io

#===========================================================================

# All link record control flags
class DbFlags:
    """TODO: doc
    """
    #-----------------------------------------------------------------------
    @staticmethod
    def from_json(data):
        return DbFlags(data['in_use'], data['is_controller'],
                       data['high_water'])
    
    #-----------------------------------------------------------------------
    @staticmethod
    def from_bytes(raw, offset=0):
        b = raw[offset]
        
        in_use = bool(b & (0b1 << 7))
        is_controller = bool(b & (0b1 << 6))
        # bits 2-5 are unused
        high_water = bool(b & (0b1 << 1))
        
        return DbFlags(in_use, is_controller, high_water)

    #-----------------------------------------------------------------------
    def __init__(self, in_use, is_controller, high_water):
        self.in_use = in_use
        self.is_controller = is_controller
        self.is_responder = not is_controller
        self.high_water = high_water

    #-----------------------------------------------------------------------
    def to_bytes(self):
        data = self.in_use << 7 | \
               self.is_controller << 6 | \
               self.high_water << 1
        return bytes( [ data ] )
    
    #-----------------------------------------------------------------------
    def to_json(self):
        return {
            'in_use' : self.in_use,
            'is_controller' : self.is_controller,
            'high_water' : self.high_water,
            }

    #-----------------------------------------------------------------------
    def __str__(self):
        return "in_use: %s type: %s used: %s" % \
            (self.in_use, 'CTRL' if self.is_controller else 'RESP',
             self.high_water)

    #-----------------------------------------------------------------------
