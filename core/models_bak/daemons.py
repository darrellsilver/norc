#
# Copyright (c) 2009, Perpetually.com, LLC.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
#     * Redistributions of source code must retain the above copyright 
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Perpetually.com, LLC. nor the names of its 
#       contributors may be used to endorse or promote products derived from 
#       this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
# POSSIBILITY OF SUCH DAMAGE.
#


"""Models relating to daemons."""

import os
import datetime

from django.db import models

from tasks import Task, TaskRunStatus

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
        db_table = 'norc_daemonstatus'
    
    region = models.ForeignKey('ResourceRegion')
    host = models.CharField(max_length=124)
    pid = models.IntegerField()
    status = models.CharField(choices=(zip(ALL_STATUSES, ALL_STATUSES)), max_length=64)
    date_started = models.DateTimeField(default=datetime.datetime.utcnow)
    date_ended = models.DateTimeField(blank=True, null=True)
    
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
    
    def get_status(self):
        return self.status
    
    def is_pause_requested(self):
        return self.get_status() == NorcDaemonStatus.STATUS_PAUSEREQUESTED
    
    def is_stop_requested(self):
        return self.get_status() == NorcDaemonStatus.STATUS_STOPREQUESTED
    
    def is_kill_requested(self):
        return self.get_status() == NorcDaemonStatus.STATUS_KILLREQUESTED
    
    def is_paused(self):
        return self.get_status() == NorcDaemonStatus.STATUS_PAUSED
    
    def is_being_stopped(self):
        return self.get_status() == NorcDaemonStatus.STATUS_STOPINPROGRESS
    
    def is_being_killed(self):
        return self.get_status() == NorcDaemonStatus.STATUS_KILLINPROGRESS
    
    def is_starting(self):
        return self.get_status() == NorcDaemonStatus.STATUS_STARTING
    
    def is_shutting_down(self):
        return self.is_stop_requested() or self.is_kill_requested()
    
    def is_running(self):
        return self.get_status() == NorcDaemonStatus.STATUS_RUNNING
    
    def is_done(self):
        return self.get_status() in (NorcDaemonStatus.STATUS_ENDEDGRACEFULLY
                                    , NorcDaemonStatus.STATUS_KILLED
                                    , NorcDaemonStatus.STATUS_ERROR
                                    , NorcDaemonStatus.STATUS_DELETED)
    
    def is_done_with_error(self):
        return self.get_status() == NorcDaemonStatus.STATUS_ERROR
    
    def is_deleted(self):
        return self.get_status() == NorcDaemonStatus.STATUS_DELETED
    
    def get_daemon_type(self):
        return 'NORC'
    
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
    

