QUEUES = {}

class MetaStatus(object):
    """"""
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
    