
import re
import random
from datetime import datetime, timedelta

from django.db.models import (Model, Manager,
    BooleanField,
    CharField,
    DateTimeField,
    PositiveIntegerField,
    ForeignKey)
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey

from norc.core.constants import SCHEDULER_FREQUENCY
from norc.norc_utils import search
from norc.norc_utils.parallel import MultiTimer
from norc.norc_utils.log import make_log

class ScheduleManager(Manager):
    def unclaimed(self):
        return self.filter(scheduler__isnull=True)
    def orphaned(self):
        cutoff = datetime.utcnow() - \
            timedelta(seconds=(SCHEDULER_FREQUENCY * 1.5))
        active = self.filter(scheduler__active=True)
        return active.filter(scheduler__heartbeat__lt=cutoff)

class BaseSchedule(Model):
    """A schedule of executions for a specific task."""
    
    objects = ScheduleManager()
    
    class Meta:
        app_label = 'core'
        abstract = True
    
    # The Task this is a schedule for.
    task_type = ForeignKey(ContentType, related_name='%(class)s_set_a')
    task_id = PositiveIntegerField()
    task = GenericForeignKey('task_type', 'task_id')
    
    # The Queue to execute the Task through.
    queue_type = ForeignKey(ContentType, related_name='%(class)s_set_b')
    queue_id = PositiveIntegerField()
    queue = GenericForeignKey('queue_type', 'queue_id')
    
    # The total number of repetitions of the Task.  0 for infinite.
    repetitions = PositiveIntegerField()
    
    # The number of repetitions remaining.
    remaining = PositiveIntegerField()
    
    # The Scheduler that has scheduled the next execution.
    scheduler = ForeignKey('Scheduler', null=True, related_name='%(class)ss')
    
    # Whether or not to make up missed executions.
    make_up = BooleanField(default=False)
    
    def enqueued(self):
        """Called when the next instance has been enqueued."""
        raise NotImplementedError
    
    def finished(self):
        """Checks whether all runs of the Schedule have been completed."""
        return self.remaining == 0 and self.repetitions > 0
    

class Schedule(BaseSchedule):
    
    # Next execution.
    next = DateTimeField(null=True)
    
    # The delay in between executions.
    period = PositiveIntegerField()
    
    @staticmethod
    def create(task, queue, start=0, reps=1, delay=0):
        if type(start) == int:
            start = timedelta(seconds=start)
        if type(start) == timedelta:
            start = datetime.utcnow() + start
        return Schedule.objects.create(task=task, queue=queue, next=start,
            repetitions=reps, remaining=reps, period=str(delay))
    
    def enqueued(self):
        """Called when the next instance has been enqueued."""
        now = datetime.utcnow()
        # Sanity check: this method should never be called before self.next.
        assert self.next < now, "Enqueued too early!"
        if self.repetitions > 0:
            self.remaining -= 1
        if not self.finished():
            period = timedelta(seconds=self.period)
            self.next += period
            while not self.make_up and self.next < now:
                self.next += period
        else:
            self.next = None
    
    

class CronSchedule(BaseSchedule):
    
    # The datetime that the next execution time is based off of.
    base = DateTimeField(null=True)
    
    _months = CharField(max_length=64)
    _days = CharField(max_length=124)
    _weekdays = CharField(max_length=32)
    _hours = CharField(max_length=124)
    _minutes = CharField(max_length=256)
    _seconds = CharField(max_length=256)
    
    MONTHS = range(1,13)
    DAYS = range(1,32)
    WEEKDAYS = range(7)
    HOURS = range(24)
    MINUTES = range(60)
    SECONDS = range(60)
    
    @staticmethod
    def create(task, queue, encoding):
        # Take in cron schedules like "weekly", etc..
        pass
    
    @staticmethod
    def parse(string):
        return map(int, string.split(','))
    
    @staticmethod
    def decode(cron):
        cron = ''.join(cron.split()) # Strip whitespace.
        valid_keys = dict(o='months', d='days', w='weekdays',
            h='hours', m='minutes', s='seconds')
        groups = re.findall(r'([a-zA-Z])+*(\*|\d(?:,*\d+)*)', cron)
        print groups
        p = {}
        for k, s in groups:
            if k in valid_keys:
                try:
                    p[k] = map(int, s.split(','))
                    p[k].sort()
                except ValueError:
                    pass
        for k in valid_keys:
            if not k in p:
                p[k] = getattr(CronSchedule, valid_keys[k].upper())
        return p['o'], p['d'], p['w'], p['h'], p['m'], p['s']
    
    def __init__(self, *args, **kwargs):
        BaseSchedule.__init__(self, *args, **kwargs)
        self._next = self.calculate_next()
        self.months = CronSchedule.parse(self._months)
        self.days = CronSchedule.parse(self._days)
        self.weekdays = CronSchedule.parse(self._weekdays)
        self.hours = CronSchedule.parse(self._hours)
        self.minutes = CronSchedule.parse(self._minutes)
        self.seconds = CronSchedule.parse(self._seconds)
    
    def enqueued(self):
        """Called when the next instance has been enqueued."""
        now = datetime.utcnow()
        # Sanity check: this method should never be called before self.next.
        assert self.next < now, "Enqueued too early!"
        if self.repetitions > 0:
            self.remaining -= 1
        if not self.finished():
            if self.make_up:
                self.base = self.next
            else:
                self.base = datetime.utcnow()
            self._next = None # Don't calculate now, but clear the old value.
    
    def _get_next(self):
        if not self._next:
            self._next = self.calculate_next()
        return self._next
    next = property(_get_next)
    
    def calculate_next(self, dt=None):
        if not dt:
            dt = self.base if self.base else datetime.utcnow()
        dt = dt.replace(seconds=dt.second + 1, microseconds=0)
        second = self.find_gte(dt.second, self.seconds)
        if not second:
            second = self.seconds[0]
            dt += timedelta(minutes=1)
        dt = dt.replace(second=second)
        minute = self.find_gte(dt.minute, self.minutes)
        if not minute:
            minute = self.minutes[0]
            dt += timedelta(hours=1)
        dt = dt.replace(minute=minute)
        hour = self.find_gte(dt.hour, self.hours)
        if not hour:
            hour = self.hours[0]
            dt += timedelta(days=1)
        dt = dt.replace(hour=hour)
        cond = lambda d: d.day in self.days and d.weekday() in self.weekdays
        one_day = timedelta(days=1)
        while not cond(dt):
            dt += one_day
        return dt
    
    def find_gte(self, p, ls):
        """Return the first element of ls that is >= p."""
        for e in ls:
            if e >= p:
                return e
    
