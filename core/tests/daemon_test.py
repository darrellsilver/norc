
"""Module for testing anything related to daemons."""

from threading import Thread

from django.test import TestCase

from norc.core.models import Daemon, DBQueue, CommandTask, Instance
from norc.core.constants import Status
from norc.norc_utils import wait_until, log

class DaemonTest(TestCase):
    """Tests for a Norc daemon."""
    
    def _get_daemon(self):
        return Daemon.objects.get(pk=self._daemon.pk)
    daemon = property(_get_daemon)
    
    def setUp(self):
        """Create the daemon and thread objects."""
        self.queue = DBQueue.objects.create(name='test')
        self._daemon = Daemon.objects.create(queue=self.queue, concurrent=4)
        # Uncomment the following line for verbose daemons.
        # self._daemon.log = log.make_log(self._daemon.log_path, echo=True)
        self.thread = Thread(target=self._daemon.start)
    
    def test_start_stop(self):    
        self.assertEqual(self.daemon.status, Status.CREATED)
        self.thread.start()
        wait_until(lambda: self.daemon.status == Status.RUNNING, 3)
        self.assertEqual(self.daemon.status, Status.RUNNING)
        self.daemon.make_request(Daemon.REQUEST_STOP)
        wait_until(lambda: Status.is_final(self.daemon.status), 5)
        self.assertEqual(self.daemon.status, Status.ENDED)
        
    def test_kill(self):
        self.thread.start()
        wait_until(lambda: self.daemon.status == Status.RUNNING, 3)
        self.assertEqual(self.daemon.status, Status.RUNNING)
        self.daemon.make_request(Daemon.REQUEST_KILL)
        wait_until(lambda: Status.is_final(self.daemon.status), 5)
        self.assertEqual(self.daemon.status, Status.KILLED)
    
    def test_pause_unpause(self):
        self.thread.start()
        wait_until(lambda: self.daemon.status == Status.RUNNING, 3)
        self.assertEqual(self.daemon.status, Status.RUNNING)
        self.daemon.make_request(Daemon.REQUEST_PAUSE)
        wait_until(lambda: self.daemon.status == Status.PAUSED, 5)
        self.assertEqual(self.daemon.status, Status.PAUSED)
        self.daemon.make_request(Daemon.REQUEST_UNPAUSE)
        wait_until(lambda: self.daemon.status == Status.RUNNING, 5)
        self.assertEqual(self.daemon.status, Status.RUNNING)
    
    # This test does not work because of an issue with subprocesses using
    # the Django test database.
    
    # def test_run_instance(self):
    #     self.thread.start()
    #     ct = CommandTask.objects.create(name='test', command='echo "blah"')
    #     _instance = Instance.objects.create(source=ct, daemon=self._daemon)
    #     instance = lambda: Instance.objects.get(pk=_instance.pk)
    #     wait_until(lambda: self.daemon.status == Status.RUNNING, 3)
    #     self.queue.push(_instance)
    #     wait_until(lambda: Status.is_final(instance().status), 5)
    #     self.assertEqual(instance().status, Status.SUCCESS)
    
    def tearDown(self):
        if self._daemon.status == Status.RUNNING:
            self._daemon.make_request(Daemon.REQUEST_KILL)
        self.thread.join(5)
        self._daemon.heart.join(5)
        assert not self.thread.isAlive()
        assert not self._daemon.heart.isAlive()
