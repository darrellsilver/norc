
"""All basic task related models."""

import sys
from datetime import datetime
import re
import subprocess

from django.db.models import (Model,
    BooleanField,
    CharField,
    DateTimeField,
    IntegerField,
    PositiveIntegerField,
    PositiveSmallIntegerField,
    ForeignKey)
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import (GenericRelation,
                                                 GenericForeignKey)

from norc import settings
from norc.core.constants import Status
from norc.norc_utils.log import make_log

class Task(Model):
    """An abstract class that represents something to be executed."""
    
    class Meta:
        app_label = 'core'
        abstract = True
    
    name = CharField(max_length=128, unique=True)
    description = CharField(max_length=512, blank=True, default='')
    date_added = DateTimeField(default=datetime.utcnow)
    timeout = PositiveIntegerField(default=0)
    instances = GenericRelation('Instance')
    
    def start(self, instance):
        """Starts the given instance.."""
        self.log = make_log(instance.log_path)
        if instance.status != Status.CREATED:
            self.log.error("Can't start an instance more than once.")
            return
        for signum in [signal.SIGINT, signal.SIGTERM, signal.SIGKILL]:
            signal.signal(signum, lambda n, f: self.kill_handler(instance))
        if self.timeout > 0:
            signal.signal(signal.SIGALRM,
                lambda n, f: self.timeout_handler(instance))
            signal.alarm(self.timeout)
        self.log.info('Starting %s.' % instance)
        self.log.start_redirect()
        try:
            success = self._run(instance)
        except Exception:
            self.log.error("Task failed with an exception!", trace=True)
            instance.status = Status.ERROR
        else:
            if success or success == None:
                instance.status = Status.SUCCESS
            else:
                instance.status = Status.FAILURE
        finally:
            self.log.info("Task ended with status %s." %
                Status.NAMES[instance.status])
            self.log.stop_redirect()
            instance.save()
    
    def _run(self, instance):
        """Provides an easy hook to give run() the instance if needed."""
        return self.run()
    
    def run(self):
        """The actual work of the Task."""
        raise NotImplementedError
    
    def kill_handler(self, instance):
        self.log.error("Kill signal received! Setting status to INTERRUPTED.")
        instance.status = Status.INTERRUPTED
        instance.save()
        sys.exit(1)
    
    def timeout_handler(self, instance):
        self.log.info("Task timed out!  Ceasing execution.")
        instance.status = Status.TIMEDOUT
        instance.save()
        sys.exit(0)
    
    def __unicode__(self):
        return u"%s '%s'" % (self.__class__.__name__, self.name)
    
    __repr__ = __unicode__
    

class BaseInstance(Model):
    """One instance (run) of a Task."""
    
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
    
    # The status of the execution.
    status = PositiveSmallIntegerField(default=Status.CREATED,
        choices=[(s, Status.NAMES[s]) for s in VALID_STATUSES])
    
    # When the instance was added to a queue.
    enqueue_date = DateTimeField(default=datetime.utcnow)
    
    # When the instance started.
    start_date = DateTimeField(null=True)
    
    # When the instance ended.
    end_date = DateTimeField(null=True)
    
    # The daemon that executed/is executing this instance.
    daemon = ForeignKey('Daemon', null=True)
    
    def start(self):
        self.start_date = datetime.datetime.utcnow()
        self.run()
        self.end_date = datetime.datetime.utcnow()
        self.save()
    
    def run(self):
        raise NotImplementedError
    
    def _get_queue(self):
        try:
            return self.daemon.queue
        except AttributeError:
            return None
    queue = property(_get_queue)
    
    def __unicode__(self):
        return u"Instance of %s, #%s" % (self.source, self.id)
    
    __repr__ = __unicode__
    

class Instance(BaseInstance):
    """Normal Instance implementation for Tasks."""
    
    # The object that spawned this instance.
    source_type = ForeignKey(ContentType)
    source_id = PositiveIntegerField()
    source = GenericForeignKey('source_type', 'source_id')
    
    # The schedule from whence this instance spawned.
    schedule = ForeignKey('Schedule', related_name='instances')
    
    # Flag for when this instance is claimed by a Scheduler.
    claimed = BooleanField(default=False)
    
    def run(self):
        self.task.start(self)
    

class CommandTask(Task):
    """Task which runs an arbitrary shell command."""
    
    command = CharField(max_length=1024)
    nice = IntegerField(default=0)
    
    INTERPRETED_SETTINGS = ['NORC_TMP_DIR', 'DATABASE_NAME', 'DATABASE_USER',
        'DATABASE_PASSWORD', 'DATABASE_HOST', 'DATABASE_PORT']
    
    @staticmethod
    def interpret(cmd):
        for s in CommandTask.INTERPRETED_SETTINGS:
            cmd = cmd.replace('$' + s, getattr(settings, s))
        def unpack_match(f):
            return lambda m: f(*m.groups())
        def datetime_parser(dt):
            def parser(s):
                decoder = dict(YYYY='%Y', MM='%m', DD='%d',
                    hh='%H', mm='%m', ss='%S')
                for k, v in decoder.items():
                    s = s.replace(k, dt.strftime(v))
                return s
            return unpack_match(parser)
        local = datetime.now()
        utc = datetime.utcnow()
        cmd = re.sub(r'\$LOCAL\{(.*?)\}', datetime_parser(local), cmd)
        cmd = re.sub(r'\$UTC\{(.*?)\}', datetime_parser(utc), cmd)
        return cmd
    
    def run(self):
        command = CommandTask.interpret(self.command)
        if self.nice:
            command = "nice -n %s %s" % (self.nice, command)
        print "Executing command...\n$ %s" % command
        sys.stdout.flush()
        exit_status = subprocess.call(command, shell=True)
        return exit_status == 0
    
