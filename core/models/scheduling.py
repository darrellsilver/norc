
import os
import re
import signal
import random
from datetime import datetime, timedelta

from django.db.models import (Model, Manager,
    BooleanField,
    CharField,
    DateTimeField,
    PositiveIntegerField,
    ForeignKey)
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import (GenericRelation,
                                                 GenericForeignKey)

from norc.core.constants import Status, SCHEDULER_FREQUENCY, SCHEDULER_LIMIT
from norc.norc_utils import search
from norc.norc_utils.parallel import MultiTimer

class ScheduleManager(Manager):
    def unclaimed(self):
        return self.filter(scheduler__isnull=True)

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
    
    # When the last instance was enqueued.
    last = DateTimeField(null=True)
    
    
    
    # The cron schedule encoded as a string.
    encoding = CharField(max_length=1024)
    
    def _get_next(self):
        if not self._next:
            self._next = self.calculate_next()
        return self._next
    
    def _set_next(self, next):
        self._next = next
    
    next = property(_get_next)#, _set_next)
    
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
    def decode(cron):
        # Defaults for each group...
        valid_keys = dict(o='months', d='days', w='weekdays',
            h='hours', m='minutes', s='seconds')
        groups = re.findall(r'([a-zA-Z])+\s*(\*|\d(?:,\s*\d+)*)', cron)
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
        o, d, w, h, m, s = CronSchedule.decode(self.encoding)
        self.months = o
        self.days = d
        self.weekdays = w
        self.hours = h
        self.minutes = m
        self.seconds = s
    
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
    
    def calculate_next(self, dt=None):
        if not dt:
            dt = self.last if self.last else datetime.utcnow()
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
    
    def calc_next(self, dt, key, valid):
        if key > len(TF.keys()):
            return dt if valid else None
        inc, cond = TF[key]
        if not valid:
            dt = inc(dt)
        if cond(dt):
            if valid:
                return self.calc_next(dt, key + 1, valid)
                
        
    

class SchedulerManager(Manager):
    def undead(self):
        """Schedulers that are active but no recent heartbeat."""
        cutoff = datetime.utcnow() - \
            timedelta(seconds=(SCHEDULER_FREQUENCY * 1.5))
        return self.filter(active=True).filter(heartbeat__lt=cutoff)
    

class Scheduler(Model):
    """Scheduling process for handling Schedules.
    
    Takes unclaimed Schedules from the database and adds their next
    instance to a timer.  At the appropriate time, the instance is
    added to its queue and the Schedule is updated.
    
    Idea: Split this up into two threads, one which continuously handles
    already claimed schedules, the other which periodically polls the DB
    for new schedules.
    
    """
    objects = SchedulerManager()
    
    class Meta:
        app_label = 'core'
    
    # Whether the Scheduler is currently running.
    active = BooleanField(default=False)
    
    # The datetime of the Scheduler's last heartbeat.  Used in conjunction
    # with the active flag to determine whether a Scheduler is still alive.
    heartbeat = DateTimeField(null=True)
    
    # The host this scheduler ran on.
    host = CharField(default=lambda: os.uname()[1], max_length=128)
    
    def is_alive(self):
        """Whether the Scheduler is still running.
        
        A Scheduler is defined as alive if it is active and its last
        heartbeat was within the last N*SCHEDULER_FREQUENCY seconds,
        for some N > 1 (preferably with a decent amount of margin). 
        
        """
        return self.active and self.heartbeat > \
            datetime.utcnow() - timedelta(seconds=(SCHEDULER_FREQUENCY * 1.5))
    
    def start(self):
        """Starts the Scheduler."""
        if not hasattr(self, 'log'):
            self.log = make_log(self.log_path)
        if self.heartbeat != None:
            raise StateException("Cannot restart a scheduler.")
        if __name__ == '__main__':
            for signum in [signal.SIGINT, signal.SIGTERM]:
                signal.signal(signum, lambda s, f: self.stop)
        self.timer = MultiTimer()
        self.active = True
        self.save()
        while self.active:
            # Check for dead but active schedulers.
            undead = Scheduler.objects.undead()
            undead.update(active=False)
            orphaned = Schedule.objects.filter(scheduler__in=undead)
            orphaned.update(scheduler=None)
            # Beat heart.
            self.heartbeat = datetime.utcnow()
            self.save()
            unclaimed = Schedule.objects.unclaimed()[:SCHEDULER_LIMIT]
            for schedule in unclaimed:
                schedule.scheduler = self
                schedule.save()
                self.add(schedule)
            time.sleep(SCHEDULER_FREQUENCY)
            self.active = Scheduler.objects.get(pk=self).active
        self.timer.cancel()
        self.timer.join()
        Schedule.objects.filter(scheduler=self).update(scheduler=None)
        for t in self.timer.tasks:
            instance = t[2][1]
            print t
            instance.claimed = False
            instance.save()
    
    def stop(self):
        """Stops the Scheduler (passively)."""
        self.active = False
        self.save()
    
    def add(self, schedule):
        """Adds the next instance for the schedule to the timer."""
        i = Instance.objects.create(source=schedule.task,
            start_date=schedule.next, schedule=schedule, claimed=True)
        self.timer.add_task(schedule.next, self.enqueue, [schedule, i])
    
    def enqueue(self, schedule, instance):
        """Called by the timer to add an instance to the queue.
        
        Try to make this method run AS QUICKLY AS POSSIBLE,
        otherwise tasks might start getting delayed if they
        are scheduled close together.
        
        """
        schedule.queue.push(instance)
        schedule.enqueued()
        if not schedule.finished():
            # self.flag.set()
            self.add(schedule)
        else:
            schedule.scheduler = None
        schedule.save()
    
    def _get_log_path(self):
        return 'scheduler/scheduler-%s' % self.id
    log_path = property(_get_log_path)
    
    def __unicode__(self):
        return u"Scheduler #%s on host %s" % (self.id, self.host)
    
    __repr__ = __unicode__
    
