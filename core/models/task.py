
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
        self.log = make_log(iteration.log_path)
        if iteration.status != Status.CREATED:
            self.log.error("Can't start an iteration more than once.")
            return
        for signum in [signal.SIGINT, signal.SIGTERM, signal.SIGKILL]:
            signal.signal(signum, lambda n, f: self.kill_handler(iteration))
        if self.timeout > 0:
            signal.signal(signal.SIGALRM,
                lambda n, f: self.timeout_handler(iteration))
            signal.alarm(self.timeout)
        self.log.start_redirect()
        try:
            success = self.run()
        except Exception:
            self.log.error("Task failed with an exception!", trace=True)
            iteration.status = Status.ERROR
        else:
            if success == False:
                iteration.status = Status.FAILURE
            else:
                iteration.status = Status.SUCCESS
        finally:
            self.log.info("Task ended with status %s." %
                Status.NAMES[iteration.status])
            self.log.stop_redirect()
            iteration.save()
    
    def run(self):
        """The actual work of the Task."""
        raise NotImplementedError
    
    def kill_handler(self, iteration):
        self.log.error("Kill signal received!  Setting status to INTERRUPTED.")
        iteration.status = Status.INTERRUPTED
        iteration.save()
        sys.exit(1)
    
    def timeout_handler(self, iteration):
        self.log.info("Task timed out!  Ceasing execution.")
        iteration.status = Status.TIMEDOUT
        iteration.save()
        sys.exit(0)
    
    def __unicode__(self):
        return u"%s '%s'" % (self.__class__.__name__, self.name)
    
    __repr__ = __unicode__
    

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
        Status.HANDLED,
        Status.ERROR,
        Status.TIMEDOUT,
        Status.INTERRUPTED,
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
    
    def __unicode__(self):
        return u"Iteration of %s, #%s" % (self.source, self.id)
    
    __repr__ = __unicode__
    

class Iteration(BaseIteration):
    
    # The schedule from whence this spawned.
    schedule = ForeignKey('Schedule', null=True, related_name='iterations')
    
    # Flag for when this iteration is claimed by a Scheduler.
    claimed = BooleanField(default=False)
    