
"""All basic task related models."""

from datetime import datetime, timedelta

from django.db.models import (Model,
    CharField,
    DateTimeField,
    IntegerField,
    PositiveIntegerField,
    SmallPositiveIntegerField)
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import (GenericRelation,
                                                 GenericForeignKey)

from norc.norc_utils.log import make_log

class Task(Model):
    """An abstract class that represents something to be executed."""
    
    class Meta:
        app_label = 'core'
        abstract = True
    
    name = CharField(max_length=128, unique=True)
    description = CharField(max_length=512, blank=True, default='')
    date_added = DateTimeField(auto_now_add=True)
    timeout = PositiveIntegerField(default=0)
    iterations = GenericRelation(Iteration)
    
    def start(self, iteration):
        """Initialize and run this Task."""
        pass
    
    def run(self):
        """The actual work of the Task."""
        raise NotImplementedError
    

class Iteration(Model):
    """One iteration (run) of a Task."""
    
    class Meta:
        app_label = 'core'
    
    STATUSES = {
        1: 'RUNNING',
        2: 'COMPLETED',
        3: 'ERROR',
        4: 'TIMEDOUT',
        # 5: 'RETRY',
        # 6: 'CONTINUE',
        # 7: 'SKIPPED',
    }
    
    task_ct = ForeignKey(ContentType)
    task_id = PositiveIntegerField()
    task = GenericForeignKey('task_ct', 'task_id', related_name='iterations')
    schedule = ForeignKey(Schedule, null=True, related_name='iterations')
    status = SmallPositiveIntegerField(default=1,
        choices=[(k, v.title()) for k, v in Iteration.STATUSES.iteritems()])
    date_started = DateTimeField(default=datetime.datetime.utcnow)
    date_ended = DateTimeField(null=True)
    daemon = ForeignKey('Daemon', related_name='iterations')
    
    def run(self):
        self.task.start()

class Schedule(Model):
    
    class Meta:
        app_label = 'core'
    
    STATUSES = {
        1: 'ACTIVE',
        2: 'COMPLETE',
    }
    
    task_type = ForeignKey(ContentType)
    task_id = PositiveIntegerField()
    task = GenericForeignKey('task_type', 'task_id')
    queue = ForeignKey('Queue')
    next = DateTimeField(null=True)
    repetitions = PositiveIntegerField()
    reps_left = PositiveIntegerField()
    delay = PositiveIntegerField()
    
    def __init__(self, task, queue, start=0, reps=1, delay=0):
        if not type(start) == datetime:
            start = datetime.utcnow() + timedelta(seconds=start)
        Model.__init__(self, task=task, queue=queue, next=start,
            repetitions=reps, reps_left=reps, delay=delay)
    
