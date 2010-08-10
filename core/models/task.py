
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
    iterations = GenericRelation(Iteration)
    
    def run(self):
        """The actual work of the Task."""
        raise NotImplementedError
    

class AbstractIteration(Model):
    """One iteration (run) of a Task."""
    
    class Meta:
        app_label = 'core'
        abstract = True
    
    VALID_STATUSES = [
        Status.CREATED
        Status.RUNNING,
        Status.SUCCESS,
        Stauts.FAILURE,
        Status.ERROR,
        Status.TIMEDOUT,
    ]
    
    # The object that spawned this iteration.
    source_type = ForeignKey(ContentType)
    source_id = PositiveIntegerField()
    source = GenericForeignKey('source_type', 'source_id')
    
    # The status of the execution.
    status = SmallPositiveIntegerField(default=Status.CREATED,
        choices=[(s, Status.NAMES[s]) for s in
            Iteration.VALID_STATUSES.iteritems()])
    
    # The date the iteration started/is to start.
    start_date = DateTimeField(default=datetime.datetime.utcnow)
    
    # The date the iteration ended.
    end_date = DateTimeField(null=True)
    
    # The daemon that executed/is executing this iteration.
    daemon = ForeignKey('Daemon', related_name='iterations', null=True)
    
    def save(self):
        Model.save(self)
        # self.log = make_log(...)
    
    def start(self):
        """Starts this iteration."""
        if Status.is_final(self.status):
            raise StateException("Can't start an iteration that is " +
                "already in a final state.")
        log = make_log(self.log_path)
        log.start_redirect()
        try:
            success = self.source.run()
            if success == None or success:
                self.status = Status.SUCCESS
            else:
                self.status = Status.FAILURE
        except Exception:
            log.error("Task failed with an exception!", trace=True)
            self.status = Status.ERROR
        except:
            log.error("Task failed with a poorly thrown exception!",
                trace=True)
            self.status = Status.ERROR
        finally:
            log.stop_redirect()
            self.save()
            
    

class Iteration(AbstractIteration):
    
    # The schedule from whence this spawned.
    schedule = ForeignKey(Schedule, null=True, related_name='iterations')
    
    # Flag for when this iteration is claimed by a Scheduler.
    claimed = BooleanField(default=False)
    