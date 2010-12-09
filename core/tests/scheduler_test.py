
"""Test schedule handling cases in the SchedulableTask class."""

import os, sys
from threading import Thread
from datetime import timedelta, datetime

from django.test import TestCase

from norc.core.models import Scheduler, Schedule, CronSchedule
from norc.core.constants import Status, Request
from norc.norc_utils import wait_until, log
from norc.norc_utils.testing import make_queue, make_task

class SchedulerTest(TestCase):
    
    @property
    def scheduler(self):
        return Scheduler.objects.get(pk=self._scheduler.pk)
    
    def setUp(self):
        self._scheduler = Scheduler.objects.create()
        self._scheduler.log = log.Log(os.devnull)
        self.thread = Thread(target=self._scheduler.start)
        self.thread.start()
        wait_until(lambda: self.scheduler.is_alive(), 3)
    
    def test_stop(self):
        self.scheduler.make_request(Request.STOP)
        self._scheduler.flag.set()
        wait_until(lambda: not self.scheduler.is_alive(), 3)
    
    def test_schedule(self):
        task = make_task()
        queue = make_queue()
        s = Schedule.create(task, queue, 0, 5)
        self._scheduler.flag.set()
        wait_until(lambda: s.instances.count() == 5, 5)
    
    def test_cron(self):
        task = make_task()
        queue = make_queue()
        s = CronSchedule.create(task, queue, 'o*d*w*h*m*s*', 3)
        self._scheduler.flag.set()
        wait_until(lambda: queue.count() == 3, 8)
        enqueued = map(lambda i: i.enqueued, s.instances)
        def fold(acc, e):
            self.assertEqual(e - acc, timedelta(seconds=1))
            return e
        reduce(fold, enqueued)
    
    def test_update_schedule(self):
        task = make_task()
        queue = make_queue()
        s = CronSchedule.create(task, queue, 'o*d*w*h*m*s*', 10)
        self._scheduler.flag.set()
        wait_until(lambda: queue.count() == 2, 5)
        s.encoding = 'o*d*w*h*m*s4'
        s.save()
        self.assertRaises(Exception,
            lambda: wait_until(lambda: s.instances.count() > 3, 3))
    
    def test_make_up(self):
        task = make_task()
        queue = make_queue()
        s = Schedule.create(task, queue, 1, 10, -10, True)
        self._scheduler.flag.set()
        wait_until(lambda: s.instances.count() == 10, 5)
        s = Schedule.create(task, queue, 60, 10, -10, False)
        self._scheduler.flag.set()
        wait_until(lambda: s.instances.count() == 1, 5)
    
    def test_cron_make_up(self):
        task = make_task()
        queue = make_queue()
        now = datetime.utcnow()
        s = CronSchedule(encoding='o*d*w*h*m*s%s' % ((now.second - 1) % 60),
            task=task, queue=queue, repetitions=0, remaining=0, make_up=False)
        s.base = now - timedelta(seconds=2)
        s.save()
        self._scheduler.flag.set()
        wait_until(lambda: s.instances.count() == 1, 3)
        
        now = datetime.utcnow()
        s = CronSchedule(encoding='o*d*w*h*m*s*',
            task=task, queue=queue, repetitions=0, remaining=0, make_up=True)
        s.base = now - timedelta(seconds=5)
        s.save()
        self._scheduler.flag.set()
        wait_until(lambda: s.instances.count() == 6, 1)
    
    def test_reload(self):
        task = make_task()
        queue = make_queue()
        now = datetime.utcnow()
        s = CronSchedule.create(task, queue, 'o*d*w*h*m*s%s' %
            ((now.second - 1) % 60), 1)
        self._scheduler.flag.set()
        wait_until(lambda: self.scheduler.cronschedules.count() == 1, 5)
        CronSchedule.objects.get(pk=s.pk).set_encoding('o*d*w*h*m*s*')
        self.scheduler.make_request(Request.RELOAD)
        self._scheduler.flag.set()
        wait_until(lambda: s.instances.count() == 1, 10)
    
    def test_duplicate(self):
        task = make_task()
        queue = make_queue()
        s = Schedule.create(task, queue, 1, 2, start=2)
        self._scheduler.flag.set()
        wait_until(lambda: self.scheduler.schedules.count() == 1, 2)
        s = Schedule.objects.get(pk=s.pk)
        s.scheduler = None
        s.save()
        self._scheduler.flag.set()
        wait_until(lambda: s.instances.count() == 2, 5)
        
    
    #def test_stress(self):
    #    task = make_task()
    #    queue = make_queue()
    #    for i in range(5000):
    #        CronSchedule.create(task, queue, 'HALFHOURLY')
    #    self._scheduler.flag.set()
    #    wait_until(lambda: self._scheduler.cronschedules.count() == 5000, 60)
    
    def tearDown(self):
        if not Status.is_final(self._scheduler.status):
            self._scheduler.make_request(Request.KILL)
        self.thread.join(15)
        assert not self.thread.isAlive()
        assert not self._scheduler.timer.isAlive()
    
