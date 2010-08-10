
""" Norc-specific constants.

Any constants required for the core execution of Norc
should be defined here if possible.

"""

# How often a scheduler can poll the database for new schedules.
SCHEDULER_FREQUENCY = 30

# How many new schedules the scheduler can pull from the database at once.
SCHEDULER_LIMIT = 1000

class MetaStatus(object):
    """Generates the NAMES attribute of the Status class."""
    
    def __init__(cls, name, bases, dct):
        super(MetaStatus, cls).__init__(name, bases, dct)
        NAMES = {}
        ALL = []
        for k, v in dct.iteritems():
            if type(v) == int:
                NAMES[v] = k
                ALL.append(v)
        dct['NAMES'] = NAMES
        dct['ALL'] = ALL
    

class Status(object):
    """Class to hold all status constants.
    
    The MetaStatus class automatically generates a NAMES attribute which
    contains the reverse dict for retrieving a status name from its value.
    
    """
    __metaclass__ = MetaStatus
    
    CREATED = 1
    RUNNING = 2
    PAUSED = 3
    
    # Final states.
    SUCCESS = ENDED = 7 # Different names for the same state: clean exit.
    KILLED = 8
    DELETED = 9
    
    # Failure states.
    FAILURE = 13
    ERROR = 14
    TIMEOUT = 15
    
    def is_final(status):
        return status >= 7
    
    def is_failure(status):
        return status >= 13
    
    FINAL_STATES = [s for s in Status.ALL, s >= 7]
    FAILURE_STATES = filter(lambda s: s >= 13, Status.ALL)
    
