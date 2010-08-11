
from datetime import datetime, timedelta

from django.db.models import (Model, Manager,
    BooleanField,
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
    task = GenericForeignKey(task_type, task_id)
    
    # The Queue to execute the Task through.
    queue_type = ForeignKey(ContentType, related_name='schedule_set2')
    queue_id = PositiveIntegerField()
    queue = GenericForeignKey(queue_type, queue_id)
    
    # The total number of repetitions of the Task.  0 for infinite.
    repetitions = PositiveIntegerField()
    
    # The number of repetitions remaining.
    remaining = PositiveIntegerField()
    
    # The delay between repetitions.
    delay = PositiveIntegerField()
    
    # When the next iteration should start.
    next = DateTimeField(null=True)
    
    # The Scheduler that has scheduled the next execution.
    scheduler = ForeignKey('Scheduler', null=True, related_name='schedules')
    
    def __init__(self, task, queue, start=0, reps=1, delay=0):
        if not type(start) == datetime:
            start = datetime.utcnow() + timedelta(seconds=start)
        Model.__init__(self, task=task, queue=queue, next=start,
            repetitions=reps, remaining=reps, delay=delay)
    
    def enqueued(self):
        """Called when the next iteration has been enqueued."""
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

# TODO: Should Scheduler have a log?  Probably.
class Scheduler(Model):
    """Scheduling process for handling Schedules.
    
    Takes unclaimed Schedules from the database and adds their next
    iteration to a timer.  At the appropriate time, the iteration is
    added to its queue and the Schedule is updated.
    
    """
    class Meta:
        app_label = 'core'
    
    # Whether the Scheduler is currently running.
    active = BooleanField(default=False)
    
    # The datetime of the Scheduler's last heartbeat.  Used in conjunction
    # with the active flag to determine whether a Scheduler is still alive.
    heartbeat = DateTimeField(null=True)
    
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
        # Use signals to catch kill commands.
        self.timer = MultiTimer()
        self.active = True
        self.save()
        while self.active:
            # TODO: Check for dead but active schedulers.
            self.heartbeat = datetime.utcnow()
            self.save()
            unclaimed = Schedule.objects.unclaimed()[:SCHEDULER_LIMIT]
            # Here we use update for DB efficiency.
            unclaimed.update(scheduler=self)
            for schedule in unclaimed:
                self.add(schedule)
            time.sleep(SCHEDULER_FREQUENCY)
            self.active = Scheduler.objects.get(pk=self).active
    
    def stop(self):
        """Stops the Scheduler (passively)."""
        self.active = False
        self.save()
    
    def add(self, schedule):
        """Adds the next iteration for the schedule to the timer."""
        self.timer.add_task(schedule.next, self.enqueue, [schedule])
    
    def enqueue(self, schedule):
        """Called by the timer to add an iteration to the queue.
        
        Try to make this method run AS QUICKLY AS POSSIBLE,
        otherwise tasks might start getting delayed if they
        are scheduled close together.
        
        """
        iteration = Iteration(source=schedule.task,
            start_date=schedule.next, schedule=schedule)
        iteration.save()
        schedule.queue.push(iteration)
        schedule.enqueued()
        if not schedule.finished():
            self.add(schedule)
        else:
            schedule.scheduler = None
        schedule.save()
    
