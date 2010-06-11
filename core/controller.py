
import os
from norc.core.models import *

def create_daemon_status(region, status=None, pid=None, host=None):
    if status == None:
        status = NorcDaemonStatus.STATUS_STARTING
    if pid == None:
        pid = os.getpid()
    if host == None:
        # or platform.unode(), platform.node(), socket.gethostname() -- which is best???
        host = os.uname()[1]
    
    status = NorcDaemonStatus(region=region
                                    , pid=pid, host=host
                                    , status=status)
    status.save()
    return status
