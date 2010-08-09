
""" Norc-specific constants.

Any constants required for the core execution of Norc
should be defined here if possible.

"""

class MetaStatus(object):
    """Generates the NAMES attribute of the Status class."""
    
    def __init__(cls, name, bases, dct):
        super(MetaStatus, cls).__init__(name, bases, dct)
        NAMES = {}
        for k, v in dct.iteritems():
            if type(v) == int:
                NAMES[v] = k
        dct['NAMES'] = NAMES

class Status(object):
    """Class to hold all status constants.
    
    The MetaStatus class automatically generates a NAMES attribute which
    contains the reverse dict for retrieving a status name from its value.
    
    """
    __metaclass__ = MetaStatus
    
    RUNNING = 1
    PAUSED = 2
    
    # Final states.
    COMPLETED = ENDED = 7 # Different names for the same state: clean exit.
    KILLED = 8
    DELETED = 9
    
    # Errored states.
    ERROR = 13
    TIMEOUT = 14
    
    def is_final(status):
        return status >= 7
    
    def is_error(status):
        return status >= 13
        
