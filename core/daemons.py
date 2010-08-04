
from multiprocessing import Process

from norc.core.models import DaemonStatus
from norc.norc_utils.log import make_log

class Daemon(object):
    """Daemons are responsible for the running of Tasks."""
    
    def __init__(self, queues):
        self.status = DaemonStatus.objects.create()
        self.log = make_log('daemons/daemon-%s' % self.status.id)
        
    
    def start(self):
        """Starts the daemon."""
        pass