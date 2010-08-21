
"""Test schedule handling cases in the SchedulableTask class."""

from threading import Thread

from django.test import TestCase

from norc.core.models import Scehduler, Schedule, DBQueue
from norc.core.constants import Status
from norc.norc_utils import wait_until, log

class SchedulerTest(TestCase):
    
    def setUp(self):
        pass
    
    def test_run_schedule(self):
        
        self._scheduler = Scheduler.objects.create()