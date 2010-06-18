
import pdb
import os
import threading

from django.test import TestCase

from norc import utils, core, settings
from norc.core import reporter
from norc.core.daemons import ForkingNorcDaemon
from norc.core.models import NorcDaemonStatus
from norc.utils import init_db

class DaemonThread(threading.Thread):
    
    def __init__(self, daemon):
        # self.threading = threading
        threading.Thread.__init__(self)
        self.daemon = daemon
    
    def run(self):
        self.daemon.run()

class TestDaemons(TestCase):
    """Tests for Norc daemons.
    
    Creates a ForkingNorcDaemon in a new thread because if you use the
    command line utility it does not use the Django test database.
    
    """
    # @staticmethod
    # def start_daemon(threading=False):
    #     cmd = ["norcd", "MY_REGION"]
    #     if threading:
    #         cmd.append("-t")
    #     return subprocess.Popen(cmd)
    
    def setUp(self):
        init_db.init_static()   # Initialize database.
        self.daemon = ForkingNorcDaemon(reporter.get_region('DEMO_REGION'),
            3, settings.NORC_LOG_DIR, False)
        DaemonThread(self.daemon).start()  # Start daemon.
        self.pid = os.getpid()
        # A lambda so it re-evaluates each time.
    
    def test_daemon_started(self):
        daemon_running = lambda: self.daemon.get_daemon_status().is_running()
        utils.wait_until(daemon_running, 5)
        # ndss = reporter.get_daemon_statuses()
        # pdb.set_trace()
        ndss = NorcDaemonStatus.objects.filter(pid=self.pid)
        self.assertEqual(len(ndss), 1)
        nds = ndss[0]
        self.assertEqual(self.daemon.get_daemon_status(), nds)
        # pdb.set_trace()
        # TODO: make this work...
        # self.assert_(nds.is_running())
    
    def tearDown(self):
        self.daemon.request_stop()
        no_daemons = lambda: self.daemon.get_daemon_status().is_done()
        utils.wait_until(no_daemons, 5)
