
import sys
import os
import random
import subprocess
import signal
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
from django.conf import settings

from norc.norc_utils.log import make_log

class Task(Model):
    
    class Meta:
        app_label = 'core'
    
    STATUSES = {
        1: 'ACTIVE',
        2: 'COMPLETE',
    }
    
    name = CharField(max_length=128, unique=True)
    description = CharField(max_length=512, blank=True, default='')
    date_added = DateTimeField(auto_now_add=True)
    timeout = IntegerField(default=0)
    next = DateTimeField(null=True)
    repetitions = PositiveIntegerField()
    delay = PositiveIntegerField()
    
    def __init__(self, , repeat=1, delay=0):
        if repeat != 1 and delay == None:
            raise TypeError("Must have a delay to have a repeat.")
        if type(target) != datetime:
            target = datetime.now() + timedelta(seconds=target)
        self.target = target
        self.repeat = repeat
        self.delay = delay
        
        
    
class Job(Task):
    "A Task with SubTasks, or a group of tasks that execute together."


class SubTask(AbstractTask):
    parent_dependencies = GenericRelation('TaskDependency',
        content_type_field='_child_task_content_type',
        object_id_field='_child_task_object_id')

class Iteration(Model):
    
    STATUSES = {
        1: 'RUNNING',
        2: 'SUCCESS',
        3: 'ERROR',
        4: 'TIMEDOUT',
        # 5: 'RETRY',
        # 6: 'CONTINUE',
        # 7: 'SKIPPED',
    }
    
    task = GenericForeignKey(...)
    status = SmallPositiveIntegerField(default=1,
        choices=[(k, v.title()) for k, v in Iteration.STATUSES.iteritems()])
    date_started = DateTimeField(default=datetime.datetime.utcnow)
    date_ended = DateTimeField(null=True)
    daemon = ForeignKey()
    # status = property...

class Daemon(Model):
    

class TaskRunStatus(models.Model):
    """The status of a Task that has ran or is running"""
    
    # @see http://docs.djangoproject.com/en/dev/ref/contrib/contenttypes/
    # or the lesser @see http://www.djangoproject.com/documentation/models/generic_relations/
    _task_content_type = models.ForeignKey(ContentType)
    _task_object_id = models.PositiveIntegerField()
    task = GenericForeignKey('_task_content_type', '_task_object_id')
    iteration = models.ForeignKey(Iteration)
    
    status = models.CharField(choices=(zip(ALL_STATUSES, ALL_STATUSES)), max_length=16)
    date_started = models.DateTimeField(default=datetime.datetime.utcnow)
    date_ended = models.DateTimeField(blank=True, null=True)
    # rename to nds
    controlling_daemon = models.ForeignKey('NorcDaemonStatus', blank=True, null=True)

class RunCommand(Task):
    """Run an arbitrary command line as a Task."""
    
    class Meta:
        db_table = settings.DB_TABLE_PREFIX + '_generic_runcommand'
    
    cmd = models.CharField(max_length=1024)
    nice = models.IntegerField(default=0)
    timeout = models.PositiveIntegerField()
    
    def get_library_name(self):
        return 'norc.core.models.RunCommand'
    def has_timeout(self):
        return True
    def get_timeout(self):
        return self.timeout
    def get_command(self, interpret_vars=False):
        if interpret_vars:
            return self.interpret_vars(self.cmd)
        else:
            return self.cmd
    
    def interpret_vars(self, cmd):
        """replace specific var names in the given string with their values.
        Provides environment-like settings available only at run time to the a cmd line task."""
        
        cmd_n = cmd
        # Settings
        cmd_n = cmd_n.replace("$NORC_TMP_DIR", settings.NORC_TMP_DIR)
        cmd_n = cmd_n.replace("$DATABASE_NAME", settings.DATABASE_NAME)
        cmd_n = cmd_n.replace("$DATABASE_USER", settings.DATABASE_USER)
        cmd_n = cmd_n.replace("$DATABASE_PASSWORD", settings.DATABASE_PASSWORD)
        cmd_n = cmd_n.replace("$DATABASE_HOST", settings.DATABASE_HOST)
        cmd_n = cmd_n.replace("$DATABASE_PORT", settings.DATABASE_PORT)
        # cmd_n = cmd_n.replace("$AWS_ACCESS_KEY_ID", settings.AWS_ACCESS_KEY_ID)
        # cmd_n = cmd_n.replace("$AWS_SECRET_ACCESS_KEY", settings.AWS_SECRET_ACCESS_KEY)
        
        # Local Dates
        now = datetime.datetime.now()
        cmd_n = cmd_n.replace("$LOCAL_YYYYMMDD.HHMMSS", "%s%02d%02d.%02d%02d%02d" \
            % (now.year, now.month, now.day, now.hour, now.minute, now.second))
        cmd_n = cmd_n.replace("$LOCAL_YYYYMMDD", "%s%02d%02d" % (now.year, now.month, now.day))
        cmd_n = cmd_n.replace("$LOCAL_MM/DD/YYYY", "%02d/%02d/%s" % (now.month, now.day, now.year))
        
        # UTC Dates
        utc = datetime.datetime.now()
        cmd_n = cmd_n.replace("$UTC_YYYYMMDD.HHMMSS", "%s%02d%02d.%02d%02d%02d" \
            % (utc.year, utc.month, utc.day, utc.hour, utc.minute, utc.second))
        cmd_n = cmd_n.replace("$UTC_YYYYMMDD", "%s%02d%02d" % (utc.year, utc.month, utc.day))
        cmd_n = cmd_n.replace("$UTC_MM/DD/YYYY", "%02d/%02d/%s" % (utc.month, utc.day, utc.year))
        
        return cmd_n
    
    def run(self):
        cmd = self.get_command(interpret_vars=True)
        if self.nice:
            cmd = "nice -n %s %s" % (self.nice, cmd)
        log.info("Running command '%s'" % (cmd))
        # make sure our output is in order up until this point for clarity
        sys.stdout.flush()
        if not sys.stdout == sys.stderr:
            sys.stderr.flush()
        exit_status = subprocess.call(cmd, shell=True, stdout=sys.stdout, stderr=sys.stderr)
        if exit_status == 0:
            return True
        else:
            return False
    
    def __unicode__(self):
        return u"%s" % self.get_name()
    

class SchedulableTask(Task):
    """Abstract class representing one task that can be scheduled in a crontab-like way"""
        
    SUPPORTED_SIMPLE_SCHEDULES = ['HALFHOURLY', 'HOURLY','DAILY','WEEKLY','MONTHLY']
    
    class Meta:
        abstract = True
    
    # represent the range of time as a string for efficiency in db; parse in and out on either end
    minute = models.CharField(max_length=1024)# 0-59
    hour = models.CharField(max_length=1024)# 0 <= hour < 24
    day_of_month = models.CharField(max_length=1024)# 1 <= day <= number of days in the given month and year
    month = models.CharField(max_length=1024)# 1 <= month <= 12
    day_of_week = models.CharField(max_length=1024)# 0-6 (Monday - Sunday)
    
    # stored actual ranges; parsed out from above char fields
    __minute_r=None; __hour_r=None; __day_of_month_r=None; __month_r=None; __day_of_week_r=None
    
    def __init__(self, *args, **kwargs):
        Task.__init__(self, *args, **kwargs)
        self._parse_schedule()
    
    def _parse_schedule(self):
        self.__minute_r = SchedulableTask.__str2range(self.minute, 0, 60)
        self.__hour_r = SchedulableTask.__str2range(self.hour, 0, 24)
        self.__day_of_month_r = SchedulableTask.__str2range(self.day_of_month, 1, 32)
        self.__month_r = SchedulableTask.__str2range(self.month, 1, 13)
        self.__day_of_week_r = SchedulableTask.__str2range(self.day_of_week, 0, 7)
    
    @staticmethod
    def __prettify_rangestr(r):
        if len(r) <= 5:
            s = u",".join(map(str, r))
        else:
            s = u"%s-%s" % (min(r), max(r))
        return s
    
    @staticmethod
    def __range2str(r, min_value, max_value):
        if type(r) == str and r == '*':
            r = range(min_value, max_value)
        elif type(r) == int:
            r = [r]
        elif not type(r) == list:
            raise TypeError, "range must be a list of ints"
        elif min(r) < min_value or max(r) >= max_value:
            raise TypeError, "range %s is not within limits %s-%s" % (r, min_value, max_value)
        return ",".join(map(str, r))
    
    @staticmethod
    def __str2range(s, min_value, max_value):
        if s in (None, '', '*'):
            return range(min_value, max_value)
        return map(int, s.split(","))
    
    @staticmethod
    def parse_schedule_predefined(schedule_name):
        assert schedule_name in SchedulableTask.SUPPORTED_SIMPLE_SCHEDULES, "Unknown schedule name '%s'" % (schedule_name)
        minute = range(0, 60)
        hour = range(0, 24)
        day_of_month = range(1, 32)
        month = range(1, 13)
        day_of_week = range(0, 7)
        
        if schedule_name in ['HALFHOURLY']:
            minute = [0,30]
        elif schedule_name in ['HOURLY','DAILY','WEEKLY','MONTHLY']:
            minute = 0
        if schedule_name in ['DAILY','WEEKLY','MONTHLY']:
            hour = 0
        if schedule_name in ['WEEKLY']:
            day_of_week = random.randint(0,6)
        if schedule_name in ['MONTHLY']:
            # TODO this is a shortcut it should be 31 when that many days in the month
            day_of_month = random.randint(1, 30)
        
        return (minute, hour, day_of_month, month, day_of_week)
    
    def unparse_schedule_predefined(self, pretty_names=False):
        minute = range(0, 60)
        hour = range(0, 24)
        day_of_month = range(1, 32)
        month = range(1, 13)
        day_of_week = range(0, 7)
        
        schedule_name = None
        
        if self.__minute_r == [0,30] \
            and self.__hour_r == hour \
            and self.__day_of_month_r == day_of_month \
            and self.__month_r == month \
            and self.__day_of_week_r == day_of_week:
            if pretty_names:
                schedule_name = 'every half hour'
            else:
                schedule_name = 'HALFHOURLY'
        elif self.__minute_r == [0] \
            and self.__hour_r == hour \
            and self.__day_of_month_r == day_of_month \
            and self.__month_r == month \
            and self.__day_of_week_r == day_of_week:
            if pretty_names:
                schedule_name = 'every hour'
            else:
                schedule_name = 'HOURLY'
        elif self.__minute_r == [0] \
            and self.__hour_r == [0] \
            and self.__day_of_month_r == day_of_month \
            and self.__month_r == month \
            and self.__day_of_week_r == day_of_week:
            if pretty_names:
                schedule_name = 'once a day'
            else:
                schedule_name = 'DAILY'
        elif self.__minute_r == [0] \
            and self.__hour_r == [0] \
            and self.__day_of_month_r == day_of_month \
            and self.__month_r == month \
            and len(self.__day_of_week_r) == 1:
            if pretty_names:
                schedule_name = 'once a week'
            else:
                schedule_name = 'WEEKLY'
        elif self.__minute_r == [0] \
            and self.__hour_r == [0] \
            and len(self.__day_of_month_r) == 1 \
            and self.__month_r == month \
            and self.__day_of_week_r == day_of_week:
            if pretty_names:
                schedule_name = 'once a month'
            else:
                schedule_name = 'MONTHLY'
        
        return schedule_name
    
    @staticmethod
    def prep_schedule_parts(minute, hour, day_of_month, month, day_of_week):
        """
        Take components as list and convert them into easily stored string lists
        and perform some sanity checks for valid times.
        EG minute=[1,2,3,4,5] => minute_r="1,2,3,4,5"
        hour='*' => hour_r="0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23"
        """
        minute_r = SchedulableTask.__range2str(minute, 0, 60)
        hour_r = SchedulableTask.__range2str(hour, 0, 24)
        day_of_month_r = SchedulableTask.__range2str(day_of_month, 1, 32)# not all months have 31 days, but doesn't matter
        month_r = SchedulableTask.__range2str(month, 1, 13)
        day_of_week_r = SchedulableTask.__range2str(day_of_week, 0, 7)
        
        return (minute_r, hour_r, day_of_month_r, month_r, day_of_week_r)
    
    def __closest_prev(self, i, list, list_is_sorted=True):
        # TODO there's a binary search here that can be done more efficiently than this
        if not list_is_sorted:
            list = sorted(list)
        for element in reversed(list):
            if element <= i:
                return element
        return None
    
    def is_due_to_run_at(self, t):
        if not t.minute in self.__minute_r:
            # 0 = 0
            return False
        if not t.hour in self.__hour_r:
            # 0 = 0
            return False
        if not t.day in self.__day_of_month_r:
            # 1st of Month = 1
            return False
        if not t.month in self.__month_r:
            # January = 0
            return False
        if not t.weekday() in self.__day_of_week_r:
            # Monday = 0
            return False
        return True
    def get_prev_due_to_run(self, until):
        """Return the last time this Task is due to run before 'until' datetime"""
        prev_time = until.replace(second=0, microsecond=0)
        minute = self.__closest_prev(prev_time.minute, self.__minute_r)
        if minute == None:
            # last run-minute has passed for this hour, roll to last in prev hour
            prev_time = prev_time.replace(minute=self.__minute_r[-1])
            prev_time -= datetime.timedelta(hours=1)
        else:
            prev_time = prev_time.replace(minute=minute)
        hour = self.__closest_prev(prev_time.hour, self.__hour_r)
        if hour == None:
            # last run-hour has passed for this day, roll to last hour & minute on prev day
            prev_time = prev_time.replace(hour=self.__hour_r[-1], minute=self.__minute_r[-1])
            prev_time -= datetime.timedelta(days=1)
        else:
            prev_time = prev_time.replace(hour=hour)
        
        # We compromise on efficiency here.  Determining prev for day/month/day-of-week
        # is a lot of moving parts b/c they all have to align together. So
        # since we determine hour & minute intelligently, we brute force back day by day
        # until we find first one that fits.
        while not self.is_due_to_run_at(prev_time):
            prev_time -= datetime.timedelta(days=1)
        return prev_time
    
    def is_due_to_run(self, iteration, asof):
        """
        True if this Task hasn't run at all in this Iteration, or 
        if it's been due to run since it last ran.
        Note that a missed run time will not be 'caught up'.
        There's currently no logic that allows multiple missed runs to catch up.
        """
        # times are in UTC
        if not Task.is_due_to_run(self, iteration, asof):
            return False
        
        status = self.get_current_run_status(iteration)
        if status == None:
            # This Task has never ran; it's guaranteed to be due
            return True
        prev_run_time = self.get_prev_due_to_run(asof)
        # Tasks run once a minute max; must round to minute for comparison
        last_run_time = status.get_date_started().replace(second=0, microsecond=0)
        # has this Task become due between last run and asof?
        return last_run_time < prev_run_time
    
    def is_allowed_to_run(self, iteration, asof=None):
        """
        Overrides Task.is_allowed_to_run() to account for TASK_TYPE_SCHEDULED.
        """
        if asof == None:
            asof = datetime.datetime.utcnow()
        
        if self.get_task_type() == SchedulableTask.TASK_TYPE_SCHEDULED:
            if not self.is_due_to_run(iteration, asof):
                return False
            if not self.parents_are_finished(iteration):
                return False
            status = self.get_current_run_status(iteration)
            if not status == None:
                # SchedulableTasks have 1 minute granularity: Don't run if most recent is from same minute
                started = status.get_date_started().replace(second=0, microsecond=0)
                asof = asof.replace(second=0, microsecond=0)
                if started == asof:
                    # it's due to run, and can, but there already is/was one running in this minute.
                    return False
            return True
        elif self.get_task_type() in (Task.ITER_TYPE_PERSISTENT, Task.ITER_TYPE_EPHEMERAL):
            # delegate to superclass for other task types
            return Task.is_allowed_to_run(self, iteration, asof)
        else:
            raise NorcInvalidStateException("Task type '%s' for '%s' is unsupported for SchedulableTasks." \
                % (self.get_task_type(), self.get_name()))
    
    def get_pretty_schedule(self):
        return u"minute:%s hour:%s day:%s day of month:%s day of week:%s" % (
            SchedulableTask.__prettify_rangestr(self.__minute_r),
            SchedulableTask.__prettify_rangestr(self.__hour_r),
            SchedulableTask.__prettify_rangestr(self.__day_of_month_r),
            SchedulableTask.__prettify_rangestr(self.__month_r),
            SchedulableTask.__prettify_rangestr(self.__day_of_week_r))
    def __unicode__(self):
        return self.get_pretty_schedule()

class NorcDaemonStatus(models.Model):
    """Track the statuses of Norc daemons."""
    
    # Daemon is starting.
    STATUS_STARTING = 'STARTING'
    # Daemon itself exited with bad error
    STATUS_ERROR = TaskRunStatus.STATUS_ERROR
    # Daemon is currently running
    STATUS_RUNNING = TaskRunStatus.STATUS_RUNNING
    # Pause has been requested
    STATUS_PAUSEREQUESTED = 'PAUSEREQUESTED'
    # Don't launch any more tasks, just wait.
    STATUS_PAUSED = 'PAUSED'
    # Stop launching tasks; exit gracefully when running tasks are complete.
    STATUS_STOPREQUESTED = 'STOPREQUESTED'
    # The daemon has received a stop request and will exit gracefully.
    STATUS_STOPINPROGRESS = 'BEING_STOPPED'
    # Stop launching tasks; kill already running tasks with error status.
    STATUS_KILLREQUESTED = 'KILLREQUESTED'
    # The daemon has received a kill request and is shutting down.
    STATUS_KILLINPROGRESS = 'BEING_KILLED'
    # Daemon was exited gracefully; no tasks were interrupted.
    STATUS_ENDEDGRACEFULLY = 'ENDED'
    # Daemon was killed; any running tasks were interrupted.
    STATUS_KILLED = 'KILLED'
    # Daemon status has been hidden for convenience.
    STATUS_DELETED = Task.STATUS_DELETED
    
    ALL_STATUSES = (STATUS_STARTING, STATUS_ERROR, STATUS_RUNNING,
        STATUS_PAUSEREQUESTED, STATUS_PAUSED, STATUS_STOPREQUESTED,
        STATUS_KILLREQUESTED, STATUS_KILLINPROGRESS, STATUS_STOPINPROGRESS,
        STATUS_ENDEDGRACEFULLY, STATUS_KILLED, STATUS_DELETED)
    
    class Meta:
        db_table = settings.DB_TABLE_PREFIX + '_daemonstatus'
    
    region = models.ForeignKey('ResourceRegion')
    host = models.CharField(max_length=124)
    pid = models.IntegerField()
    status = models.CharField(
        choices=(zip(ALL_STATUSES, ALL_STATUSES)), max_length=64)
    date_started = models.DateTimeField(default=datetime.datetime.utcnow)
    date_ended = models.DateTimeField(blank=True, null=True)
    
    def get_daemon_type(self):
        # TODO This is a temporary hack until we can backfill
        # a daemon_type database field.
        if 'norc.sqs' in settings.INSTALLED_APPS:
            try:
                from norc.sqs.models import SQSTaskRunStatus
                SQSTaskRunStatus.objects.filter(controlling_daemon=self)[0]
                # self.sqstaskrunstatus_set.all()[0]
                return 'SQS'
            except IndexError:
                pass
        return 'NORC'
        
        # tms_c = self.taskrunstatus_set.count()
        # if 'norc.sqs' in settings.INSTALLED_APPS:
        #     sqs_c = self.sqstaskrunstatus_set.count()
        # else:
        #     sqs_c = 0
        # if tms_c > 0 and sqs_c == 0:
        #     return 'NORC'
        # elif tms_c == 0 and sqs_c > 0:
        #     return 'SQS'
        # else:
        #     return 'NORC'
    # daemon_type = property(get_daemon_type)
    
    @staticmethod
    def create(region, daemon_type, status=None, pid=None, host=None):
        if status == None:
            status = NorcDaemonStatus.STATUS_STARTING
        if pid == None:
            pid = os.getpid()
        if host == None:
            # or platform.unode(), platform.node(), socket.gethostname() -- which is best???
            host = os.uname()[1]
        
        status = NorcDaemonStatus(
            region=region, pid=pid, host=host, status=status)
        status.save()
        return status
    
    def get_id(self):
        return self.id
    
    def thwart_cache(self):
        """
        Django caches this object, so if someone changes 
        the database directly this object doesn't see that change.
        We must call this hack to return a new instance of this object, 
        reflecting the database's latest state.
        If the record no longer exists in the database, a DoesNotExist error is raised
        Perhaps there's something in this answer about db types and refreshes?
        Also, QuerySet._clone() will reproduce, but this is almost as good.
        http://groups.google.com/group/django-users/browse_thread/thread/e25cec400598c06d
        """
        # TODO how do you do this natively to Django???
        return NorcDaemonStatus.objects.get(id=self.id)
    
    def set_status(self, status):
        assert status in NorcDaemonStatus.ALL_STATUSES, \
            "Unknown status '%s'" % (status)
        self.status = status
        if not status == TaskRunStatus.STATUS_RUNNING:
            self.date_ended = datetime.datetime.utcnow()
        self.save()

    def get_task_statuses(self, status_filter='all', since_date=None):
        """
        return the statuses (not the tasks) for all tasks run(ning) by this daemon
        date_started: limit to statuses with start date since given date, 
                    or all if date_started=None (the default)
        """
        task_statuses = self.taskrunstatus_set.all()
        status_filter = status_filter.lower()
        TRS_CATS = TaskRunStatus.STATUS_CATEGORIES
        #sqs_statuses = self.sqstaskrunstatus_set.filter(controlling_daemon=self)
        if not since_date == None:
            task_statuses = task_statuses.filter(date_started__gte=since_date)
            #sqs_statuses = sqs_statuses.filter(date_started__gte=since_date)
        if status_filter != 'all' and status_filter in TRS_CATS:
            only_statuses = TRS_CATS[status_filter.lower()]
            task_statuses = task_statuses.filter(status__in=only_statuses)
            #filtered.extend(sqs_statuses.filter(status__in=only_statuses))
        return task_statuses
    
    def __unicode__(self):
        base = u"id:%3s host:%s pid:%s" % (self.id, self.host, self.pid)
        if self.is_running():
            return u"running %s started %s" % (base, self.date_started)
        elif self.is_starting():
            return u"starting %s asof %s" % (base, self.date_started)
        elif self.is_shutting_down():
            return u"ending %s" % (base)
        else:
            return u"finished %s ran %s - %s" % (base, self.date_started, self.date_ended)
        
    def __str__(self):
        return str(self.__unicode__())
    
    __repr__ = __str__
    
