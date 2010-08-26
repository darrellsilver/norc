
""" Norc-specific constants.

Any constants required for the core execution of Norc
should be defined here if possible.

"""

# The maximum number of tasks a Daemon is allowed to run at once.
CONCURRENCY_LIMIT = 4

# How often a scheduler can poll the database for new schedules.
SCHEDULER_PERIOD = 5

# How many new schedules the scheduler can pull from the database at once.
SCHEDULER_LIMIT = 1000

TASK_MODELS = []

class MetaStatus(type):
    """Generates the NAMES attribute of the Status class."""
    
    def __new__(cls, name, bases, dct):
        """Magical function to dynamically create NAME and ALL."""
        NAME = {}
        ALL = []
        for k, v in dct.iteritems():
            if type(v) == int:
                NAME[v] = k
                ALL.append(v)
        dct['NAME'] = NAME
        dct['ALL'] = ALL
        return super(MetaStatus, cls).__new__(cls, name, bases, dct)
    
    @property
    def GROUPS(self):
        """Used for accessing groups of Statuses by a string name."""
        return {
            'running': [self.RUNNING],
            'succeeded': filter(lambda s: s >= 7 and s < 13, self.ALL),
            'failed': filter(lambda s: s > 13, self.ALL),
        }

class Status(object):
    """Class to hold all status constants.
    
    The MetaStatus class automatically generates a NAMES attribute which
    contains the reverse dict for retrieving a status name from its value.
    
    The numbers should probably be moved further apart, but SUCCESS being
    7 and FAILURE being 13 just seems so fitting...
    
    """
    __metaclass__ = MetaStatus
    
    # Transitive states.
    CREATED = 1         # Created but nothing else.
    RUNNING = 2         # Is currently running.
    PAUSED = 3          # Currently paused.
    STOPPING = 4        # In the process of stopping; should become ENDED.
    
    # Final states.
    SUCCESS = 7         # Succeeded.
    ENDED = 8           # Ended gracefully.
    KILLED = 9          # Forcefully killed.
    HANDLED = 12        # Was ERROR, but the problem's been handled.
    
    # Failure states.
    FAILURE = 13        # User defined failure (Task returned False).
    ERROR = 14          # There was an error during execution.
    TIMEDOUT = 15       # The execution timed out.
    INTERRUPTED = 16    # Execution was interrupted before completion.
    
    @staticmethod
    def is_final(status):
        """Whether the given status counts as final."""
        return status >= 7
    
    @staticmethod
    def is_failure(status):
        """Whether the given status counts as a failure."""
        return status >= 13
    
