
"""Module for testing anything related to executors."""

import os
from threading import Thread

from django.test import TestCase

from norc.core.models import Executor, DBQueue, CommandTask, Instance
from norc.core.constants import Status
from norc.norc_utils import wait_until, log

class ExecutorTest(TestCase):
    """Tests for a Norc executor."""
    
    def setUp(self):
        """Create the executor and thread objects."""
        self.queue = DBQueue.objects.create(name='test')
        self._executor = Executor.objects.create(queue=self.queue, concurrent=4)
        self._executor.log = log.Log(os.devnull)
        self.thread = Thread(target=self._executor.start)
    
    def test_start_stop(self):    
        pass
    
    def tearDown(self):
        pass
    
