
"""Module for testing anything related to executors."""

import os
from threading import Thread

from django.test import TestCase

from norc.core.models import Executor, DBQueue, CommandTask, Instance
from norc.core.constants import Status, Request
from norc.norc_utils import wait_until, log

class ExecutorTest(TestCase):
    """Tests for a Norc executor."""
    
    @property
    def executor(self):
        return Executor.objects.get(pk=self._executor.pk)
    
    def setUp(self):
        """Create the executor and thread objects."""
        self.queue = DBQueue.objects.create(name='test')
        self._executor = Executor.objects.create(queue=self.queue, concurrent=4)
        self._executor.log = log.Log(os.devnull, echo=True)
        self.thread = Thread(target=self._executor.start)
    
    def test_start_stop(self):    
        self.assertEqual(self.executor.status, Status.CREATED)
        self.thread.start()
        wait_until(lambda: self.executor.status == Status.RUNNING, 3)
        self.assertEqual(self.executor.status, Status.RUNNING)
        self.executor.make_request(Request.STOP)
        wait_until(lambda: Status.is_final(self.executor.status), 5)
        self.assertEqual(self.executor.status, Status.ENDED)
        
    def test_kill(self):
        self.thread.start()
        wait_until(lambda: self.executor.status == Status.RUNNING, 3)
        self.assertEqual(self.executor.status, Status.RUNNING)
        self.executor.make_request(Request.KILL)
        wait_until(lambda: Status.is_final(self.executor.status), 5)
        self.assertEqual(self.executor.status, Status.KILLED)
    
    def test_pause_resume(self):
        self.thread.start()
        wait_until(lambda: self.executor.status == Status.RUNNING, 3)
        self.assertEqual(self.executor.status, Status.RUNNING)
        self.executor.make_request(Request.PAUSE)
        wait_until(lambda: self.executor.status == Status.PAUSED, 5)
        self.assertEqual(self.executor.status, Status.PAUSED)
        self.executor.make_request(Request.RESUME)
        wait_until(lambda: self.executor.status == Status.RUNNING, 5)
        self.assertEqual(self.executor.status, Status.RUNNING)
    
    # This test does not work because of an issue with subprocesses using
    # the Django test database.
    
    # def test_run_instance(self):
    #     self.thread.start()
    #     ct = CommandTask.objects.create(name='test', command='echo "blah"')
    #     _instance = Instance.objects.create(task=ct, executor=self._executor)
    #     instance = lambda: Instance.objects.get(pk=_instance.pk)
    #     wait_until(lambda: self.executor.status == Status.RUNNING, 3)
    #     self.queue.push(_instance)
    #     wait_until(lambda: Status.is_final(instance().status), 5)
    #     self.assertEqual(instance().status, Status.SUCCESS)
    
    def tearDown(self):
        if not Status.is_final(self._executor.status):
            print self._executor.make_request(Request.KILL)
        self.thread.join(7)
        self._executor.heart.join(7)
        assert not self.thread.isAlive()
        assert not self._executor.heart.isAlive()
