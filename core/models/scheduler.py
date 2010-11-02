
"""The Norc Scheduler is defined here.

Norc requires that at least one of these is running at all times.

"""

import os
import re
import signal
import random
import time
from datetime import datetime, timedelta
from threading import Thread, Event
import itertools

# from django.db.models.query import QuerySet
from django.db.models import (Model, Manager,
    BooleanField,
    CharField,
    DateTimeField,
    PositiveSmallIntegerField)

from norc.core.models.task import Instance
from norc.core.models.schedules import Schedule, CronSchedule
from norc.core.models.daemon import Daemon
from norc.core.constants import (Status, Request,
                                 SCHEDULER_PERIOD, 
                                 SCHEDULER_LIMIT,
                                 HEARTBEAT_PERIOD,
                                 HEARTBEAT_FAILED)
from norc.norc_utils import search
from norc.norc_utils.parallel import MultiTimer
from norc.norc_utils.log import make_log
from norc.norc_utils.django_extras import queryset_exists, get_object
from norc.norc_utils.django_extras import QuerySetManager
from norc.norc_utils.backup import backup_log

class Scheduler(Daemon):
    """Scheduling process for handling Schedules.
    
    Takes unclaimed Schedules from the database and adds their next
    instance to a timer.  At the appropriate time, the instance is
    added to its queue and the Schedule is updated.
    
    Idea: Split this up into two threads, one which continuously handles
    already claimed schedules, the other which periodically polls the DB
    for new schedules.
    
    """
    class Meta:
        app_label = 'core'
        db_table = 'norc_scheduler'
    
    objects = QuerySetManager()
    
    class QuerySet(Daemon.QuerySet):
        """Custom manager/query set for Scheduler."""
        
        def undead(self):
            """Schedulers that are active but the heart isn't beating."""
            cutoff = datetime.utcnow() - timedelta(seconds=HEARTBEAT_FAILED)
            return self.filter(active=True).filter(heartbeat__lt=cutoff)

        def alive(self):
            cutoff = datetime.utcnow() - timedelta(seconds=HEARTBEAT_FAILED)
            return self.filter(active=True).filter(heartbeat__gte=cutoff)
    
    # All the statuses executors can have.  See constants.py.
    VALID_STATUSES = [
        Status.CREATED,
        Status.RUNNING,
        Status.PAUSED,
        Status.STOPPING,
        Status.ENDED,
        Status.ERROR,
    ]
    
    VALID_REQUESTS = [
        Request.STOP,
        Request.KILL,
        Request.PAUSE,
        Request.RESUME,
    ]
    
    # The status of this scheduler.
    status = PositiveSmallIntegerField(default=Status.CREATED,
        choices=[(s, Status.NAME[s]) for s in VALID_STATUSES])
    
    # A state-change request.
    request = PositiveSmallIntegerField(null=True,
        choices=[(r, Request.NAME[r]) for r in VALID_REQUESTS])
    
    def __init__(self, *args, **kwargs):
        super(type(self), self).__init__(self, *args, **kwargs)
        self.timer = MultiTimer()

    def start(self):
        """Starts the Scheduler."""
        # Temporary check until multiple schedulers is supported fully.
        if Scheduler.objects.alive().count() > 0:
            print "Cannot run more than one scheduler at a time."
            return
        super(type(self), self).start(self)
    
    def run(self):
        """Main run loop of the Scheduler."""
        self.timer.start()
        
        while not Status.is_final(self.status):
            self.flag.clear()
            
            # Clean up orphaned schedules and undead schedulers.
            Schedule.objects.orphaned().update(scheduler=None)
            CronSchedule.objects.orphaned().update(scheduler=None)
            
            cron = CronSchedule.objects.unclaimed()[:SCHEDULER_LIMIT]
            simple = Schedule.objects.unclaimed()[:SCHEDULER_LIMIT]
            for schedule in itertools.chain(cron, simple):
                self.log.info('Claiming %s.' % schedule)
                schedule.scheduler = self
                schedule.save()
                self.add(schedule)
            
            self.wait()
            self.active = Scheduler.objects.get(pk=self.pk).active
        
        cron = self.cronschedules.all()
        simple = self.schedules.all()
        claimed_count = cron.count() + simple.count()
        if claimed_count > 0:
            self.log.info('Cleaning up %s schedules.' % claimed_count)
            cron.update(scheduler=None)
            simple.update(scheduler=None)
    
    def clean_up(self):
        self.timer.cancel()
        self.timer.join()
    
    def handle_request(self):
        """Called when a request is found."""
        self.log.info("Request received: %s" % Request.NAME[self.request])
        
        if self.request == Executor.REQUEST_PAUSE:
            self.set_status(Status.PAUSED)
        
        elif self.request == Executor.REQUEST_RESUME:
            if self.status != Status.PAUSED:
                self.log.info("Must be paused to resume; clearing request.")
            else:
                self.set_status(Status.RUNNING)
        
        elif self.request == Executor.REQUEST_STOP:
            self.set_status(Status.STOPPING)
        
        elif self.request == Executor.REQUEST_KILL:
            # for p in self.processes.values():
            #     p.terminate()
            for pid, p in self.processes.iteritems():
                self.log.info("Killing process for %s." % p.instance)
                os.kill(pid, signal.SIGTERM)
            self.set_status(Status.KILLED)
        
        self.request = None
        self.save()
    
    def wait(self):
        """Waits on the flag."""
        super(type(self), self).wait(self, SCHEDULER_PERIOD)
    
    def add(self, schedule):
        """Adds the schedule to the timer."""
        self.log.debug('Adding %s to timer for %s.' %
            (schedule, schedule.next))
        self.timer.add_task(schedule.next, self._enqueue, [schedule])
    
    def _enqueue(self, schedule):
        """Called by the timer to add an instance to the queue."""
        updated_schedule = get_object(type(schedule), pk=schedule.pk)
        if updated_schedule == None:
            self.log.info('%s was removed.' % schedule)
            return
        schedule = updated_schedule
        
        if not schedule.scheduler == self:
            self.log.info('%s is no longer tied to this scheduler.')
            return
        instance = Instance.objects.create(
            task=schedule.task, schedule=schedule)
        self.log.info('Enqueuing %s.' % instance)
        schedule.queue.push(instance)
        schedule.enqueued()
        if not schedule.finished():
            self.add(schedule)
        else:
            schedule.scheduler = None
            schedule.save()
    
    @property
    def log_path(self):
        return 'schedulers/scheduler-%s' % self.id
    
    def __unicode__(self):
        return u"Scheduler #%s on host %s" % (self.id, self.host)
    
    __repr__ = __unicode__
    
