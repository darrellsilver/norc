
"""All basic task related models."""

import datetime

from django.db.models import (Model,
    BooleanField,
    CharField,
    DateTimeField,
    PositiveIntegerField,
    PositiveSmallIntegerField,
    ForeignKey)
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import (GenericRelation,
                                                 GenericForeignKey)

from norc.core.constants import Status
from norc.core.exceptions import StateException
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
    iterations = GenericRelation('Iteration')
    
    def start(self, iteration):
        """Starts the given iteration.."""
        if iteration.status != Status.CREATED:
            raise StateException("Can't start an iteration more than once.")
        log = make_log(iteration.log_path)
        log.start_redirect()
        try:
            success = self.run()
        except Exception:
            log.error("Task failed with an exception!", trace=True)
            iteration.status = Status.ERROR
        except:
            log.error("Task failed with a poorly thrown exception!",
                trace=True)
            iteration.status = Status.ERROR
        else:
            if success == None or success:
                iteration.status = Status.SUCCESS
            else:
                iteration.status = Status.FAILURE
        finally:
            log.info("Task ended with status %s." %
                Status.NAMES[iteration.status])
            log.stop_redirect()
            iteration.save()
    
    def run(self):
        """The actual work of the Task."""
        raise NotImplementedError
    

class BaseIteration(Model):
    """One iteration (run) of a Task."""
    
    class Meta:
        app_label = 'core'
        abstract = True
    
    VALID_STATUSES = [
        Status.CREATED,
        Status.RUNNING,
        Status.SUCCESS,
        Status.FAILURE,
        Status.ERROR,
        Status.TIMEOUT,
        Status.HANDLED,
    ]
    
    # The object that spawned this iteration.
    source_type = ForeignKey(ContentType)
    source_id = PositiveIntegerField()
    source = GenericForeignKey('source_type', 'source_id')
    
    # The status of the execution.
    status = PositiveSmallIntegerField(default=Status.CREATED,
        choices=[(s, Status.NAMES[s]) for s in VALID_STATUSES])
    
    # The date the iteration started/is to start.
    start_date = DateTimeField(default=datetime.datetime.utcnow)
    
    # The date the iteration ended.
    end_date = DateTimeField(null=True)
    
    # The daemon that executed/is executing this iteration.
    daemon = ForeignKey('Daemon', null=True)
    
    def run(self):
        self.source.start(self)

class Iteration(BaseIteration):
    
    # The schedule from whence this spawned.
    schedule = ForeignKey('Schedule', null=True, related_name='iterations')
    
    # Flag for when this iteration is claimed by a Scheduler.
    claimed = BooleanField(default=False)
    