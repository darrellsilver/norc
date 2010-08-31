
"""Test schedule handling cases in the SchedulableTask class."""

import unittest
import re

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
        self.t = CommandTask.objects.create(
            name='TestTask', command='echo "Testing, 1, 2, 3."')
        self.q = DBQueue.objects.create(name='Test')
        # self.cron = CronSchedule.create(self.t, self.q, 'WEEKLY')
    
    def test_validate(self):
        v = lambda s: CronSchedule.validate(s)[0]
        self.assertEqual(v('o1d1w1h1m1s1'), 'o1d1w1h1m1s1')
        self.assertTrue(re.match(r'^o\*d\*w\*h\*m\*s\d+$', v('')))
        self.assertEqual(v('d1w1h1m1s1'), 'o*d1w1h1m1s1')
        self.assertEqual(v(' d 1 , 2 s 1 '), 'o*d1,2w*h*m*s1')
        
        self.assertRaises(AssertionError, lambda: v('adf'))
        self.assertRaises(AssertionError, lambda: v('o1,13'))
    
    def test_pretty_name(self):
        make = lambda p: CronSchedule.create(self.t, self.q, p)
        self.assertEqual(make('HALFHOURLY').pretty_name(), 'HALFHOURLY')
        self.assertEqual(make('HOURLY').pretty_name(), 'HOURLY')
        self.assertEqual(make('DAILY').pretty_name(), 'DAILY')
        self.assertEqual(make('WEEKLY').pretty_name(), 'WEEKLY')
        self.assertEqual(make('MONTHLY').pretty_name(), 'MONTHLY')
    
