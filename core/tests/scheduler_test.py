
"""Test schedule handling cases in the SchedulableTask class."""

from threading import Thread

from django.test import TestCase

from norc.core.models import Scheduler, Schedule, CronSchedule
from norc.core.constants import Status
from norc.norc_utils import wait_until, log
from norc.norc_utils.testing import make_queue, make_task

class SchedulerTest(TestCase):
    
    @property
    def scheduler(self):
        return Scheduler.objects.get(pk=self._scheduler.pk)
    
    def setUp(self):
        self._scheduler = Scheduler.objects.create()
        # self._scheduler.log = log.make_log(
        #     self._scheduler.log_path, echo=True)
        self.thread = Thread(target=self._scheduler.start)
        self.thread.start()
        wait_until(lambda: self.scheduler.is_alive(), 3)
    
    def test_stop(self):
        self.scheduler.stop()
        wait_until(lambda: not self.scheduler.is_alive(), 3)
    
    def test_schedule(self):
        task = make_task()
        queue = make_queue()
        s = Schedule.create(task, queue, 0, 5)
        wait_until(lambda: s.instances.count() == 5, 5)
        s = Schedule.create(task, queue, 1, 10, -10, True)
        wait_until(lambda: s.instances.count() == 10, 5)
    
    def test_cron(self):
        task = make_task()
        queue = make_queue()
        s = CronSchedule.create(task, queue, 'o*d*w*h*m*s*', 2)
        wait_until(lambda: queue.count() == 2, 7)
    
    def tearDown(self):
        if self._scheduler.active:
            self._scheduler.stop()
            # wait_until(lambda: not self._scheduler.is_alive(), 3)
        self.thread.join(5)
        self._scheduler.timer.join(5)
        assert not self.thread.isAlive()
        assert not self._scheduler.timer.isAlive()
    
