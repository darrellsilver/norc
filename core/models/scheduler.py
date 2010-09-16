
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

from django.db.models import (Model, Manager,
    BooleanField,
    CharField,
    DateTimeField)

from norc.core.models.task import Instance
from norc.core.models.schedules import Schedule, CronSchedule
from norc.core.constants import (SCHEDULER_PERIOD, 
                                 SCHEDULER_LIMIT,
                                 HEARTBEAT_PERIOD)
from norc.norc_utils import search
from norc.norc_utils.parallel import MultiTimer
from norc.norc_utils.log import make_log
from norc.norc_utils.django_extras import queryset_exists

class SchedulerManager(Manager):
    """Custom manager for Scheduler."""
    
    def undead(self):
        """Schedulers that are alive (active) but the heart isn't beating."""
        cutoff = datetime.utcnow() - \
            timedelta(seconds=(HEARTBEAT_PERIOD + 1))
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
    
    # When this scheduler was started.
    started = DateTimeField(null=True)
    
    # When this scheduler was started.
    ended = DateTimeField(null=True)
    
    def __init__(self, *args, **kwargs):
        Model.__init__(self, *args, **kwargs)
        self.flag = Event()
        self.timer = MultiTimer()
        self.heart = Thread(target=self.heart_run)
        self.heart.daemon = True
        
    def is_alive(self):
        """Whether the Scheduler is still running.
        
        A Scheduler is defined as alive if it is active and its last
        heartbeat was within the last N*SCHEDULER_PERIOD seconds,
        for some N > 1 (preferably with a decent amount of margin). 
        
        """
        return self.active and self.heartbeat and self.heartbeat > \
            datetime.utcnow() - timedelta(seconds=(HEARTBEAT_PERIOD + 1))
    
    def heart_run(self):
        while self.active:
            self.heartbeat = datetime.utcnow()
            self.save()
            time.sleep(HEARTBEAT_PERIOD)
    
    def start(self):
        """Starts the Scheduler."""
        if self.active or self.heartbeat != None:
            print "Cannot restart a scheduler."
            return
        if not hasattr(self, 'log'):
            self.log = make_log(self.log_path)
        if __name__ == '__main__':
            for signum in [signal.SIGINT, signal.SIGTERM]:
                signal.signal(signum, self.signal_handler)
        self.timer.start()
        self.active = True
        self.heartbeat = self.started = datetime.utcnow()
        self.save()
        self.heart.start()
        self.log.start_redirect()
        self.log.info('Starting %s...' % self)
        try:
            self.run()
        except:
            self.log.error('An unhandled exception occurred within ' +
                'the run function!', trace=True)
        else:
            self.log.info('%s is shutting down...' % self)
            self.timer.cancel()
            self.timer.join()
            cron = self.cronschedules.all()
            simple = self.schedules.all()
            claimed_count = cron.count() + simple.count()
            if claimed_count > 0:
                self.log.info('Cleaning up %s schedules.' % claimed_count)
                cron.update(scheduler=None)
                simple.update(scheduler=None)
            self.log.info('%s exited cleanly.' % self)
        finally:
            self.log.stop_redirect()
            self.log.close()
            self.ended = datetime.utcnow()
            self.active = False
            self.save()
    
    def run(self):
        """Main run loop of the Scheduler."""
        while self.active:
            self.flag.clear()
            
            # Clean up orphaned schedules and undead schedulers.
            Schedule.objects.orphaned().update(scheduler=None)
            CronSchedule.objects.orphaned().update(scheduler=None)
            Scheduler.objects.undead().update(active=False)
            
            cron = CronSchedule.objects.unclaimed()[:SCHEDULER_LIMIT]
            simple = Schedule.objects.unclaimed()[:SCHEDULER_LIMIT]
            for schedule in itertools.chain(cron, simple):
                self.log.info('Claiming %s.' % schedule)
                schedule.scheduler = self
                schedule.save()
                self.add(schedule)
            
            self.wait()
            self.active = Scheduler.objects.get(pk=self.pk).active
    
    def wait(self):
        """Waits on the flag.
        
        The try is necessary because for some reason signal handling
        doesn't work from within the flag.wait()
        
        """
        try:
            self.flag.wait(SCHEDULER_PERIOD)
        except KeyboardInterrupt:
            self.signal_handler(signal.SIGINT)
        except SystemExit:
            self.signal_handler(signal.SIGTERM)
    
    def add(self, schedule):
        """Adds the schedule to the timer."""
        self.log.debug('Adding %s to timer for %s.' %
            (schedule, schedule.next))
        self.timer.add_task(schedule.next, self._enqueue, [schedule])
    
    def _enqueue(self, schedule):
        """Called by the timer to add an instance to the queue."""
        if not queryset_exists(type(schedule).objects.filter(pk=schedule.pk)):
            self.log.info('%s was removed.' % schedule)
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
    
    def signal_handler(self, signum, frame=None):
        """Handles signal interruption."""
        sig_name = None
        # A reverse lookup to find the signal name.
        for attr in dir(signal):
            if attr.startswith('SIG') and getattr(signal, attr) == signum:
                sig_name = attr
                break
        self.log.info("Signal '%s' received!" % sig_name)
        if signum == signal.SIGINT:
            self.stop()
        else:
            self.stop()
            # sys.exit(1)     # Maybe?
    
    def stop(self):
        """Stops the Scheduler (passively)."""
        self.active = False
        self.save()
        self.flag.set()
    
    @property
    def log_path(self):
        return 'schedulers/scheduler-%s' % self.id
    
    def __unicode__(self):
        return u"Scheduler #%s on host %s" % (self.id, self.host)
    
    __repr__ = __unicode__
    
