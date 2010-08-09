
"""All basic task related models."""

import datetime

from django.db.models import (Model,
    CharField,
    DateTimeField,
    IntegerField,
    PositiveIntegerField,
    SmallPositiveIntegerField,
    ForeignKey)
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import (GenericRelation,
                                                 GenericForeignKey)

from norc.core.constants import Status
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
    
    def run(self):
        """The actual work of the Task."""
        raise NotImplementedError
    

class Iteration(Model):
    """One iteration (run) of a Task."""
    
    class Meta:
        app_label = 'core'
    
    VALID_STATUSES = [
        Status.RUNNING,
        Status.COMPLETED,
        Status.ERROR,
        Status.TIMEDOUT,
    ]
    
    # The object that spawned this iteration.
    spawner_type = ForeignKey(ContentType)
    spawner_id = PositiveIntegerField()
    spawner = GenericForeignKey('spawner_type', 'spawner_id')
    
    # The status of the execution.
    status = SmallPositiveIntegerField(default=Status.RUNNING,
        choices=[(s, Status.NAMES[s]) for s in
            Iteration.VALID_STATUSES.iteritems()])
    
    # The date the iteration started.
    date_started = DateTimeField(default=datetime.datetime.utcnow)
    
    # The date the iteration ended.
    date_ended = DateTimeField(null=True)
    
    # The daemon executing this iteration.
    daemon = ForeignKey('Daemon', related_name='iterations')
    
    # The schedule from whence this spawned.
    schedule = ForeignKey(Schedule, null=True, related_name='iterations')
    
    # Flag for when this iteration is claimed by a Scheduler.
    claimed = BooleanField(default=False)
    
    def save(self):
        Model.save(self)
        self.log = make_log()
    
    def start(self):
        """Starts this iteration."""
        if Status.is_final(self.status):
            
    
