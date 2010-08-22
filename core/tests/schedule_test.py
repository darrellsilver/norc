
"""Test schedule handling cases in the SchedulableTask class."""

import unittest


from django.test import TestCase

from norc.core.models import CommandTask, DBQueue, Schedule, CronSchedule
from norc.norc_utils import wait_until, log

class ScheduleTest(TestCase):
    
    def setUp(self):
        pass
    
    def test_run_schedule(self):
        pass

class CronScheduleTest(TestCase):
    
    def setUp(self):
        self.t = CommandTask.objects.create(name='ls', command='ls')
        self.q = DBQueue.objects.create(name='test')
        # self.cron = CronSchedule.create(self.t, self.q, 'WEEKLY')
    
    def test_encoding(self):
        pass
        # print self.cron.encode()

    def test_pretty_name(self):
        make = lambda p: CronSchedule.create(self.t, self.q, p)
        self.assertEqual(make('HALFHOURLY').pretty_name(), 'HALFHOURLY')
        self.assertEqual(make('HOURLY').pretty_name(), 'HOURLY')
        self.assertEqual(make('DAILY').pretty_name(), 'DAILY')
        self.assertEqual(make('WEEKLY').pretty_name(), 'WEEKLY')
        self.assertEqual(make('MONTHLY').pretty_name(), 'MONTHLY')
        
        