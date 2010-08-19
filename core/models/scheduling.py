
from datetime import datetime, timedelta
import re

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
from norc.norc_utils.parallel import MultiTimer

class ScheduleManager(Manager):
    def unclaimed(self):
        return self.filter(scheduler__isnull=True)

class Schedule(Model):
    """A schedule of executions for a specific task."""
    
    objects = ScheduleManager()
    
    class Meta:
        app_label = 'core'
    
    # The Task this is a schedule for.
    task_type = ForeignKey(ContentType)
    task_id = PositiveIntegerField()
    task = GenericForeignKey('task_type', 'task_id')
    
    # The Queue to execute the Task through.
    queue_type = ForeignKey(ContentType, related_name='schedule_set2')
    queue_id = PositiveIntegerField()
    queue = GenericForeignKey('queue_type', 'queue_id')
    
    # The total number of repetitions of the Task.  0 for infinite.
    repetitions = PositiveIntegerField()
    
    # The number of repetitions remaining.
    remaining = PositiveIntegerField()
    
    # The Scheduler that has scheduled the next execution.
    scheduler = ForeignKey('Scheduler', null=True, related_name='schedules')
    
    # When the last instance was started.
    last = DateTimeField(null=True)
    
    
    schedukey = CharField(max_length=1024)
    
    MONTHS = set(xrange(1,13))
    DAYS = set(xrange(1,32))
    WEEKDAYS = set(xrange(7))
    HOURS = set(xrange(24))
    MINUTES = set(xrange(60))
    SECONDS = set(xrange(60))
    
    @staticmethod
    def create(task, queue, start=0, reps=1, delay=0):
        if type(start) == int:
            start = timedelta(seconds=start)
        if type(start) == timedelta:
            start = datetime.utcnow() + start
        return Model.objects.create(task=task, queue=queue, next=start,
            repetitions=reps, remaining=reps, key=str(delay))
    
    
    @staticmethod
    def create_cron(task, queue, cron):
        # Take in cron schedules like "weekly", etc..
        pass
    
    @staticmethod
    def parse(cron):
        
        groups = re.findall(r'([a-zA-Z])+(\d(?:,\d+)*)', cron)
        
    
    def enqueued(self):
        """Called when the next instance has been enqueued."""
        # Sanity check: this method should never be called before self.next.
        assert self.next < datetime.utcnow(), "Enqueued too early!"
        if self.repetitions > 0:
            self.remaining -= 1
        if not self.finished():
            self.next += timedelta(seconds=self.delay)
        else:
            self.next = None
        # Let the Scheduler handle saving for efficiency.
        # self.save()
    
    def finished(self):
        """Checks whether all runs of the Schedule have been completed."""
        return self.remaining == 0 and self.repetitions > 0
    

class SchedulerManager(Manager):
    def undead(self):
        """Schedulers that are active but no recent heartbeat."""
        cutoff = datetime.utcnow() - \
            timedelta(seconds=(SCHEDULER_FREQUENCY * 1.5))
        return self.filter(active=True).filter(heartbeat__lt=cutoff)


# TODO: Should Scheduler have a log and/or status?  Probably maybe.
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
        if self.heartbeat != None:
            raise StateException("Cannot restart a scheduler.")
        # TODO: Use signals to catch SIGINT and SIGTERM...
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
            # Here we use update for DB efficiency.
            unclaimed.update(scheduler=self)
            for schedule in unclaimed:
                self.add(schedule)
            time.sleep(SCHEDULER_FREQUENCY) # TODO: Switch to a flag?
            self.active = Scheduler.objects.get(pk=self).active
        self.timer.join()
    
    def stop(self):
        """Stops the Scheduler (passively)."""
        self.active = False
        self.save()
    
    def add(self, schedule):
        """Adds the next instance for the schedule to the timer."""
        i = Instance.objects.create(source=schedule.task,
            start_date=schedule.next, schedule=schedule)
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
    
    def __unicode__(self):
        return u"Scheduler #%s on host %s" % (self.id, self.host)
    
    __repr__ = __unicode__
    
