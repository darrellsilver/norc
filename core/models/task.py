
"""All basic task related models."""

import sys
from datetime import datetime
import re
import subprocess
import signal

from django.db.models import (Model, query, base,
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
from norc.core.constants import Status, TASK_MODELS, INSTANCE_MODELS
from norc.norc_utils.log import make_log
from norc.norc_utils.django_extras import QuerySetManager
from norc.norc_utils.parsing import parse_since
from norc.norc_utils.backup import backup_log

class NorcInterruptException(BaseException):
    pass

class NorcTimeoutException(BaseException):
    pass

class MetaTask(base.ModelBase):
    def __init__(self, name, bases, dct):
        base.ModelBase.__init__(self, name, bases, dct)
        if not self._meta.abstract:
            TASK_MODELS.append(self)
    

class Task(Model):
    """An abstract class that represents something to be executed."""
    
    __metaclass__ = MetaTask
    class Meta:
        app_label = 'core'
        abstract = True
    
    name = CharField(max_length=128, unique=True, null=True)
    description = CharField(max_length=512, blank=True, default='')
    date_added = DateTimeField(default=datetime.utcnow)
    timeout = PositiveIntegerField(default=0)
    instances = GenericRelation('Instance',
        content_type_field='task_type', object_id_field='task_id')
    
    schedules = GenericRelation('Schedule',
        content_type_field='task_type', object_id_field='task_id')
    cronschedules = GenericRelation('CronSchedule',
        content_type_field='task_type', object_id_field='task_id')
    
    def start(self, instance):
        """A hook function for easily changing the parameters to run().
        
        This is useful because some types of task (such as Job) need access
        to the instance object that is currently running, but we don't want
        to make run have any parameters by default.
        
        """
        return self.run()
    
    def run(self):
        """The actual work of the Task should be done in this function."""
        raise NotImplementedError
    
    def __unicode__(self):
        return u"%s %s" % (type(self).__name__, self.name or "#" + self.id)
    
    __repr__ = __unicode__

class MetaInstance(base.ModelBase):
    def __init__(self, name, bases, dct):
        base.ModelBase.__init__(self, name, bases, dct)
        if not self._meta.abstract:
            INSTANCE_MODELS.append(self)

class AbstractInstance(Model):
    """One instance (run) of a Task."""
    
    __metaclass__ = MetaInstance
    
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
        choices=[(s, Status.name(s)) for s in VALID_STATUSES])
    
    # When the instance was added to a queue.
    enqueued = DateTimeField(default=datetime.utcnow)
    
    # When the instance started.
    started = DateTimeField(null=True)
    
    # When the instance ended.
    ended = DateTimeField(null=True)
    
    # The executor of this instance.
    executor = ForeignKey('core.Executor', null=True,
        related_name='_%(class)ss')
    
    def start(self):
        if not hasattr(self, 'log'):
            self.log = make_log(self.log_path)
        if self.status != Status.CREATED:
            self.log.error("Can't start an instance more than once.")
            return
        try:
            for signum in [signal.SIGINT, signal.SIGTERM]:
                signal.signal(signum, self.kill_handler)
        except ValueError:
            pass
        if self.timeout > 0:
            signal.signal(signal.SIGALRM, self.timeout_handler)
            signal.alarm(self.timeout)
        self.log.info('Starting %s.' % self)
        self.log.start_redirect()
        self.status = Status.RUNNING
        self.started = datetime.utcnow()
        self.save()
        try:
            success = self.run()
        except Exception:
            self.log.error("Task failed with an exception!", trace=True)
            self.status = Status.ERROR
        except NorcInterruptException:
            self.log.error("Interrupt signal received!")
            self.status = Status.INTERRUPTED
        except NorcTimeoutException:
            self.log.info("Task timed out!  Ceasing execution.")
            self.status = Status.TIMEDOUT
        else:
            if success or success == None:
                self.status = Status.SUCCESS
            else:
                self.status = Status.FAILURE
        finally:
            self.ended = datetime.utcnow()
            self.save()
            self.log.info("Task ended with status %s." %
                Status.name(self.status))
            self.log.stop_redirect()
            self.log.close()
            sys.exit(0 if self.status == Status.SUCCESS else 1)
    
    def run(self):
        raise NotImplementedError
    
    def kill_handler(self, *args, **kwargs):
        raise NorcInterruptException()
    
    def timeout_handler(self, *args, **kwargs):
        raise NorcTimeoutException()
    
    @property
    def source(self):
        return None
    
    @property
    def queue(self):
        try:
            return self.executor.queue
        except AttributeError:
            return None
    
    def __unicode__(self):
        return u"<%s #%s>" % (type(self).__name__, self.id)
    
    __repr__ = __unicode__
    

class Instance(AbstractInstance):
    """Normal Instance implementation for Tasks."""
    
    class Meta:
        app_label = 'core'
        db_table = 'norc_instance'
    
    objects = QuerySetManager()
    
    class QuerySet(query.QuerySet):
        
        def since(self, since):
            if type(since) == str:
                since = parse_since(since)
            return self.exclude(ended__lt=since) if since else self
        
        def status_in(self, statuses):
            if isinstance(statuses, basestring):
                statuses = Status.GROUPS(statuses)
            return self.filter(status__in=statuses) if statuses else self
        
        def from_queue(self, q):
            return self.filter(executor__queue_id=q.id,
                executor__queue_type=ContentType.objects.get_for_model(q).id)
    
    # The object that spawned this instance.
    task_type = ForeignKey(ContentType, related_name='instances')
    task_id = PositiveIntegerField()
    task = GenericForeignKey('task_type', 'task_id')
    
    # The schedule from whence this instance spawned.
    schedule_type = ForeignKey(ContentType, null=True)
    schedule_id = PositiveIntegerField(null=True)
    schedule = GenericForeignKey('schedule_type', 'schedule_id')
    
    def run(self):
        return self.task.start(self)
    
    @property
    def timeout(self):
        return self.task.timeout
    
    @property
    def source(self):
        return self.task.name
    
    @property
    def log_path(self):
        return 'tasks/%s/%s/%s-%s' % (self.task.__class__.__name__,
            self.task.name, self.task.name, self.id)
    
    def __unicode__(self):
        return u'<Instance #%s of %s>' % (self.id, self.task)
    
    __repr__ = __unicode__
    

class CommandTask(Task):
    """Task which runs an arbitrary shell command."""
    
    class Meta:
        app_label = 'core'
        db_table = 'norc_commandtask'
    
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
        exit_status = subprocess.call(command, shell=True,
            stdout=sys.stdout, stderr=sys.stderr)
        if exit_status in [126, 127]:
            raise ValueError("Invalid command: %s" % command)
        return exit_status == 0
    
