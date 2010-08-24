
import re
import random
from datetime import datetime, timedelta

from django.db.models import (Model, Manager, Q,
    BooleanField,
    CharField,
    DateTimeField,
    PositiveIntegerField,
    ForeignKey)
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey

from norc.core.constants import SCHEDULER_PERIOD
from norc.norc_utils import search
from norc.norc_utils.parallel import MultiTimer
from norc.norc_utils.log import make_log

class ScheduleManager(Manager):
    
    @property
    def unfinished(self):
        return self.filter(Q(remaining__gt=0) | Q(repetitions=0))
    
    def unclaimed(self):
        return self.unfinished.filter(scheduler__isnull=True)
    
    def orphaned(self):
        wait = SCHEDULER_PERIOD * 1.5
        cutoff = datetime.utcnow() - timedelta(seconds=wait)
        active = self.unfinished.filter(scheduler__active=True)
        return active.exclude(scheduler__heartbeat__gt=cutoff)
    

class BaseSchedule(Model):
    """A schedule of executions for a specific task."""
    
    objects = ScheduleManager()
    
    class Meta:
        app_label = 'core'
        abstract = True
    
    # The Task this is a schedule for.
    task_type = ForeignKey(ContentType, related_name='%(class)ss')
    task_id = PositiveIntegerField()
    task = GenericForeignKey('task_type', 'task_id')
    
    # The Queue to execute the Task through.
    queue_type = ForeignKey(ContentType, related_name='%(class)s_set')
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
    
    @property
    def instances(self):
        """Custom implemented to avoid cascade-deleting instances."""
        schedule_type = ContentType.objects.get_for_model(self)
        return Instance.objects.filter(
            schedule_type__pk=schedule_type.pk, schedule_id=self.id)
    
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
            repetitions=reps, remaining=reps, period=delay)
    
    def enqueued(self):
        """Called when the next instance has been enqueued."""
        now = datetime.utcnow()
        # Sanity check: this method should never be called before self.next.
        assert self.next < now, "Enqueued too early!"
        if self.repetitions > 0:
            self.remaining -= 1
        if not self.finished() and self.period > 0:
            period = timedelta(seconds=self.period)
            self.next += period
            while not self.make_up and self.next < now:
                self.next += period
        elif self.finished():
            self.next = None
        return 
    

ri = random.randint

def _make_halfhourly():
    m = ri(0, 29)
    return 'o*d*w*h*m%s,%ss%s' % (m, m + 30, ri(0, 59))

def _make_hourly():
    return 'o*d*w*h*m%ss%s' % (ri(0, 59), ri(0, 59))

def _make_daily():
    return 'o*d*w*h%sm%ss%s' % (ri(0, 23), ri(0, 59), ri(0, 59))

def _make_weekly():
    return 'o*d*w%sh%sm%ss%s' % (ri(0, 6), ri(0, 23), ri(0, 59), ri(0, 59))

def _make_monthly():
    return 'o*d%sw*h%sm%ss%s' % (ri(1, 28), ri(0, 23), ri(0, 59), ri(0, 59))

class CronSchedule(BaseSchedule):
    
    # The datetime that the next execution time is based off of.
    base = DateTimeField(null=True)
    
    # The string encoding of the schedule.
    encoding = CharField(max_length=864)
    
    MONTHS = range(1,13)
    DAYS = range(1,32)
    DAYSOFWEEK = range(7)
    HOURS = range(24)
    MINUTES = range(60)
    SECONDS = range(60)
    
    FIELDS = ['months', 'days', 'daysofweek', 'hours', 'minutes', 'seconds']
    
    MAKE_PREDEFINED = {
        'HALFHOURLY': _make_halfhourly,
        'HOURLY': _make_hourly,
        'DAILY': _make_daily,
        'WEEKLY': _make_weekly,
        'MONTHLY': _make_monthly,
    }
    
    @staticmethod
    def create(task, queue, encoding, reps=0, make_up=False):
        if type(encoding) == tuple:
            pass
        if encoding.upper() in CronSchedule.MAKE_PREDEFINED:
            encoding = CronSchedule.MAKE_PREDEFINED[encoding.upper()]()
        return CronSchedule.objects.create(task=task, encoding=encoding,
            queue=queue, repetitions=reps, remaining=reps, make_up=make_up)
    
    @staticmethod
    def parse(string):
        return map(int, string.split(','))
    
    @staticmethod
    def unparse(ls):
        return ','.join(map(str, ls))
    
    @staticmethod
    def decode(enc):
        enc = ''.join(enc.split()) # Strip whitespace.
        valid_keys = dict(o='months', d='days', w='daysofweek',
            h='hours', m='minutes', s='seconds')
        groups = re.findall(r'([a-zA-Z])+(\*|\d+(?:,\d+)*)', enc)
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
                if k == 's':    # Default to only one second.
                    p[k] = [random.choice(p[k])]
        return p['o'], p['d'], p['w'], p['h'], p['m'], p['s']
    
    def __init__(self, *args, **kwargs):
        BaseSchedule.__init__(self, *args, **kwargs)
        self.months, self.days, self.daysofweek, self.hours, \
            self.minutes, self.seconds = CronSchedule.decode(self.encoding)
        self._next = self.calculate_next()
    
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
                self.base = now
            self._next = None # Don't calculate now, but clear the old value.
    
    @property
    def next(self):
        if not self._next:
            self._next = self.calculate_next()
        return self._next
    
    def calculate_next(self, dt=None):
        if not dt:
            dt = self.base if self.base else datetime.utcnow()
        dt = dt.replace(microsecond=0)
        dt += timedelta(seconds=1)
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
        cond = lambda d: d.day in self.days and d.weekday() in self.daysofweek
        one_day = timedelta(days=1)
        while not cond(dt):
            dt += one_day
        return dt
    
    def find_gte(self, p, ls):
        """Return the first element of ls that is >= p."""
        # TODO: Binary search.
        for e in ls:
            if e >= p:
                return e
    
    def encode(self):
        tup = ()
        for field in CronSchedule.FIELDS:
            list_ = getattr(self, field)
            if list_ == getattr(CronSchedule, field.upper()):
                tup += ('*',)
            else:
                tup += (CronSchedule.unparse(list_),)
        return 'o%sd%sw%sh%sm%ss%s' % tup
        
    def pretty_name(self):
        """Returns the pretty (predefined) name for this schedule."""
        searchs = {
            r'o\*d\*w\*h\*m(\d+),(\d+)s\d+': 'HALFHOURLY',
            r'o\*d\*w\*h\*m\d+s\d+': 'HOURLY',
            r'o\*d\*w\*h\d+m\d+s\d+': 'DAILY',
            r'o\*d\*w\d+h\d+m\d+s\d+': 'WEEKLY',
            r'o\*d\d+w\*h\d+m\d+s\d+': 'MONTHLY',
        }
        encoding = self.encode()
        for regex, name in searchs.items():
            m = re.match(regex, encoding)
            if m:
                mins = map(int, m.groups())
                if m.groups() and abs(mins[0] - mins[1]) != 30:
                    continue
                return name
    
