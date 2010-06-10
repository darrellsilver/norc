#!/usr/bin/python

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



############################################
#
#
# The Norc daemon:
# Polls Norc for tasks to run, and runs them.
# Each Task is run in a seperate thread
#
#
# TODO:
#  - Eliminate the delay between a 
#    task becoming ready to run and running it.
#    - This could be achieved if the daemon was listening on a port
#    - Does MySQL support listening for DB events?
#  - max daemons per machine or dont bother?
#  - errors/message that occur in the daemon in the task thread are logged to the task, rather than the daemon.
#
#
#Darrell
#04/13/2009
############################################

import sys, os, time
import signal
import traceback
import datetime
import threading    # if using thread for running Tasks
import subprocess   # if using forking for running Tasks

from django.db import models

from norc import settings
from norc.core import manage
from tasks import Task, TaskRunStatus
from norc.utils import log
log = log.Log(settings.LOGGING_DEBUG)

# TODO: Can these be run not as daemons?

class NorcDaemon(object):
    """Abstract daemon; subclasses implement the running of Tasks."""
    
    __poll_frequency__ = None
    __daemon_status__ = None
    __break_tasks_to_run_loop__ = False
    
    def __init__(self, region, poll_frequency):
        self.__poll_frequency__ = poll_frequency
        self.__daemon_status__ = NorcDaemonStatus.create(region)
    
    def get_poll_frequency(self):
        return self.__poll_frequency__
    def get_daemon_status(self):
        return self.__daemon_status__
    def __set_daemon_status__(self, daemon_status):
        self.__daemon_status__ = daemon_status
    
    def __do_run__(self):
        """Main daemon loop"""
        log.info("%s %s..." % (self.get_name(), str(self.get_daemon_status())))
        if settings.DEBUG:
            log.info("WARNING: settings.DEBUG is True: daemon will gobble up memory b/c django stores SQL queries.")
        self.get_daemon_status().set_status(NorcDaemonStatus.STATUS_RUNNING)
        last_status = self.get_daemon_status().get_status()
        while True:
            if not last_status == self.get_daemon_status().get_status():
                log.info("tmsd state changed: %s -> %s" % (last_status, self.get_daemon_status().get_status()))
                last_status = self.get_daemon_status().get_status()
            self.__set_daemon_status__(self.get_daemon_status().thwart_cache())# see note in this method definition
            if self.get_daemon_status().is_stop_requested() or \
               self.get_daemon_status().is_being_stopped():
                # don't kick off more tasks, but wait for those running to finish on their own
                self.get_daemon_status().set_status(NorcDaemonStatus.STATUS_STOPINPROGRESS)
                num_running_tasks = self.get_num_running_tasks()
                if num_running_tasks == 0:
                    log.info("tmsd stop requested and no more tasks. Ending gracefully.")
                    self.get_daemon_status().set_status(NorcDaemonStatus.STATUS_ENDEDGRACEFULLY)
                    return True
                else:
                    log.info("tmsd stop requested; waiting for %s task(s) to finish." % (num_running_tasks))
            elif self.get_daemon_status().is_kill_requested() or self.get_daemon_status().is_being_killed():
                running_tasks = self.get_running_tasks()
                if len(running_tasks) == 0:
                    log.info("tmsd kill requested but no tasks running. Ending gracefully.")
                    self.get_daemon_status().set_status(NorcDaemonStatus.STATUS_ENDEDGRACEFULLY)
                    return True
                else:
                    log.info("tmsd kill requested; interrupting %s task(s) and stopping immediately." % (len(running_tasks)))
                    self.get_daemon_status().set_status(NorcDaemonStatus.STATUS_KILLINPROGRESS)
                    for running_task in running_tasks:
                        # There's no way to actually interrupt python threads
                        # mark the task as ended in error, and leave it up to
                        # main() to call SIGKILL on this process.
                        log.info("interrupting task '%s'." % (running_task), indent_chars=4)
                        try:
                            running_task.interrupt()
                        except Exception, e:
                            log.error("Could not interrupt Task '%s'" % (running_task), e)
                    self.get_daemon_status().set_status(NorcDaemonStatus.STATUS_KILLED)
                    return False
            elif self.get_daemon_status().is_pause_requested():
                log.info("tmsd pause requested.  Will just sit here.")
                self.get_daemon_status().set_status(NorcDaemonStatus.STATUS_PAUSED)
            elif self.get_daemon_status().is_paused():
                log.debug("tmsd paused.  Just sittin' here.")
            elif self.get_daemon_status().is_running():
                self.__break_tasks_to_run_loop__ = False# We're definitely running; don't break unless told to now.
                self.run_batch()
            else:
                raise Exception("Don't know how to handle daemon state '%s'" % (self.tmsd_status.get_status()))
            # wait here before polling again
            time.sleep(self.get_poll_frequency())
        raise Exception("The main loop exited somehow without throwing an error. Bug?")
    
    def run_batch(self):
        tasks_to_run = manage.get_tasks_allowed_to_run(end_completed_iterations=True, max_to_return=10)
        num_running_tasks = self.get_num_running_tasks()
        log.debug("tmsd running %s task(s), at least %s task(s) due to run" % (num_running_tasks, len(tasks_to_run)))
        need_resource_types = []
        for (task, iteration) in tasks_to_run:
            if self.__break_tasks_to_run_loop__:
                # some other thread (request_stop) doesn't want me to continue.  Stop here.
                break
            # check that there are currently sufficient resources to prevent
            # erroneously thinking this task can be run when it cannot.
            # There will be occasional cases where race conditions mean a task is not run when
            # it could be, but there are many more cases when this will save threads.
            if type(task) in need_resource_types:
                # A Task of this type already returned unavailable resources; don't check again.
                # This should be an efficiency gain for the running of Tasks to prevent 
                # excessive polling of the resources table when there are likely no new resources.
                #log.info("Assuming no resources avail for Task type '%s'" % (type(task)))
                pass
            elif task.resources_available_to_run(self.get_daemon_status().get_region()):
                try:
                    self.start_task(task, iteration)
                except Exception, e:
                    log.error("Could not run Task '%s'" % (task), e)
            else:
                need_resource_types.append(type(task))
    
    def run(self):
        """Start this daemon"""
        try:
            ended_gracefully = self.__do_run__()
            return ended_gracefully
        except Exception, e:
            self.get_daemon_status().set_status(NorcDaemonStatus.STATUS_ERROR)
            log.error("norcd suffered an internal error. BAD!", e)
            return False
    
    def request_stop(self):
        log.info("tmsd Sending stop request...")
        self.get_daemon_status().set_status(NorcDaemonStatus.STATUS_STOPREQUESTED)
        self.__break_tasks_to_run_loop__ = True
    def request_kill(self):
        log.info("tmsd Sending kill request...")
        self.get_daemon_status().set_status(NorcDaemonStatus.STATUS_KILLREQUESTED)
        self.__break_tasks_to_run_loop__ = True
    
    def get_num_running_tasks(self):
        """Return the number of currently running Tasks for this daemon"""
        return len(self.get_running_tasks())
    def get_name(self):
        """Return a name for this daemon implementation"""
        raise NotImplementedError
    def get_running_tasks(self):
        """Returns list of currently running RunnableTask's"""
        raise NotImplementedError
    def start_task(self, task, iteration):
        """Start the given Task in the given Iteration"""
        raise NotImplementedError

class NorcDaemonStatus(models.Model):
    """Track the statuses of Norc daemons."""
    
    DAEMON_TYPE_TMS = 'TMS'
    DAEMON_TYPE_SQS = 'SQS'
    
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
    
    ALL_STATUSES = (STATUS_STARTING
        , STATUS_ERROR, STATUS_RUNNING
        , STATUS_PAUSEREQUESTED, STATUS_PAUSED
        , STATUS_STOPREQUESTED, STATUS_KILLREQUESTED
        , STATUS_KILLINPROGRESS, STATUS_STOPINPROGRESS
        , STATUS_ENDEDGRACEFULLY, STATUS_KILLED
        , STATUS_DELETED)
    
    class Meta:
        db_table = 'norc_daemonstatus'
    
    region = models.ForeignKey('ResourceRegion')
    host = models.CharField(max_length=124)
    pid = models.IntegerField()
    status = models.CharField(choices=(zip(ALL_STATUSES, ALL_STATUSES)), max_length=64)
    date_started = models.DateTimeField(default=datetime.datetime.utcnow)
    date_ended = models.DateTimeField(blank=True, null=True)
    
    @staticmethod
    def create(region, status=None, pid=None, host=None):
        if status == None:
            status = NorcDaemonStatus.STATUS_STARTING
        if pid == None:
            pid = os.getpid()
        if host == None:
            # or platform.unode(), platform.node(), socket.gethostname() -- which is best???
            host = os.uname()[1]
        
        status = NorcDaemonStatus(region=region
                                        , pid=pid, host=host
                                        , status=status)
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
    def get_region(self):
        return self.region
    def set_status(self, status):
        assert status in NorcDaemonStatus.ALL_STATUSES, "Unknown status '%s'" % (status)
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
        # TODO This is sloppy!
        norc_c = self.taskrunstatus_set.count()
        sqs_c = self.sqstaskrunstatus_set.count()
        if norc_c > 0 and sqs_c == 0:
            return NorcDaemonStatus.DAEMON_TYPE_TMS
        elif norc_c == 0 and sqs_c > 0:
            return NorcDaemonStatus.DAEMON_TYPE_SQS
        else:
            return NorcDaemonStatus.DAEMON_TYPE_TMS
    def get_task_statuses(self, only_statuses=None, date_started=None):
        """
        return the statuses (not the tasks) for all tasks run(ning) by this daemon
        date_started: limit to statuses with start date since given date, 
                    or all if date_started=None (the default)
        """
        filtered = []
        task_statuses = self.taskrunstatus_set.filter(controlling_daemon=self)
        sqs_statuses = self.sqstaskrunstatus_set.filter(controlling_daemon=self)
        if not date_started == None:
            task_statuses = task_statuses.filter(date_started__gte=date_started)
            sqs_statuses = sqs_statuses.filter(date_started__gte=date_started)
        if only_statuses == None:
            filtered.extend(task_statuses.all())
            filtered.extend(sqs_statuses.all())
        else:
            filtered.extend(task_statuses.filter(status__in=only_statuses))
            filtered.extend(sqs_statuses.filter(status__in=only_statuses))
        return filtered
    
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
    

class RunnableTask(object):
    """Abstract interface for a runnable Task."""
    
    __task__ = None
    __iteration__ = None
    __daemon_status__ = None
    
    def __init__(self, task, iteration, daemon_status):
        self.__task__ = task
        self.__iteration__ = iteration
        self.__daemon_status__ = daemon_status
    
    def get_task(self):
        return self.__task__
    def get_iteration(self):
        return self.__iteration__
    def get_daemon_status(self):
        return self.__daemon_status__
    
    def run(self):
        """Run this Task!"""
        raise NotImplementedError
    def interrupt(self):
        """Interrupt this Task."""
        raise NotImplementedError

class ThreadedTaskLogger(object):
    """
    Direct output from each threaded task to the appropriate log file
    instead of mixed with the daemon or other Tasks.
    This must replace sys.stdout &| sys.stderr to be of any use.
    
    This thread was inspirational:
    http://mail.python.org/pipermail/python-list/2000-June/041632.html
    """
    
    __orig_stdout__ = None
    __orig_stderr__ = None
    __log_dir__ = None
    daemon_id_for_log = None
    buffer_data = None
    open_files = None
    
    def __init__(self, log_dir, daemon_id_for_log, buffer_data):
        if not os.path.exists(log_dir):
            raise Exception("log_dir '%s' not found!" % (log_dir))
        self.__log_dir__ = log_dir
        self.daemon_id_for_log = daemon_id_for_log
        if not daemon_id_for_log == None:
            log.info("NORCD stderr & stdout will be in '%s'" \
                % (self._get_daemon_log_file_name()))
        self.buffer_data = buffer_data
        self.open_files = {}
    
    def _get_daemon_log_file_name(self):
        assert not self.daemon_id_for_log == None, "daemon_id_for_log is None! BUG!"
        fp = "%s/_norcd/norcd.%s" % (self.__log_dir__, self.daemon_id_for_log)
        return fp
    
    def _get_log_file(self, fp):
        if not self.open_files.has_key(fp):
            if not os.path.exists(os.path.dirname(fp)):
                os.mkdir(os.path.dirname(fp))
            self.open_files[fp] = open(fp, 'a')
        return self.open_files[fp]
    
    def write_to_task_log(self, task, data):
        fh = self._get_log_file(task.get_log_file())
        fh.write(data)
        if not self.buffer_data:
            fh.flush()
    
    def write_to_daemon_log(self, data):
        fh = self._get_log_file(self._get_daemon_log_file_name())
        fh.write(data)
        if not self.buffer_data:
            fh.flush()
    
    def write(self, data):
        try:
            current_thread = threading.currentThread()
            if type(current_thread) == TaskInThread:
                self.write_to_task_log(current_thread.get_task(), data)
            elif not self.daemon_id_for_log == None:
                self.write_to_daemon_log(data)
            else:
                # all messages for daemon are sent to stdout
                self.__orig_stdout__.write(data)
                if not self.buffer_data:
                    self.__orig_stdout__.flush()
        except Exception, e:
            try:
                if type(current_thread) == TaskInThread:
                    self.__orig_stderr__.write("Exception occured writing log for Task id:%s \"%s\". BAD!\n" 
                        % (current_thread.get_task().get_id(), current_thread.get_task()))
                else:
                    self.__orig_stderr__.write("Exception occured writing log: '%s'. BAD!\n" 
                        % (e))
            except:
                self.__orig_stderr__.write("Exception occured writing log and couldn't determine task. BAD!\n")
        except:
            pass
    
    def close_log(self, task):
        fp = task.get_log_file()
        if self.open_files.has_key(fp):
            try:
                self.open_files[fp].close()
            except:
                pass
            try:
                del self.open_files[fp]
            except:
                pass
    def close_all(self):
        to_close = self.open_files.values()
        log.debug("Closing %s log file(s)" % (len(to_close)))
        for fh in to_close:
            fh.close()
    
    def start_redirect(self):
        self.__orig_stdout__ = sys.stdout
        self.__orig_stderr__ = sys.stderr
        sys.stdout = self
        sys.stderr = self
    def stop_redirect(self):
        self.close_all()
        sys.stdout = self.__orig_stdout__
        sys.stderr = self.__orig_stderr__


class TaskInProcess(RunnableTask):
    
    RUN_TASK_EXE = 'tmsd_run_task'
    
    __log_dir__ = None
    __subprocess__ = None
    
    def __init__(self, task, iteration, daemon_status, log_dir):
        RunnableTask.__init__(self, task, iteration, daemon_status)
        self.__log_dir__ = log_dir
    
    def run(self):
        #log.info("Starting Task \"%s\" in new process" % (self.get_task().get_name()))
        log_file_name = self.get_task().get_log_file()
        # TODO change this to get log file in RUN_TASK_EXE
        cmd = [TaskInProcess.RUN_TASK_EXE
            , "--daemon_status_id", str(self.get_daemon_status().get_id())
            , "--iteration_id", str(self.get_iteration().get_id())
            , "--task_library", str(self.get_task().get_library_name())
            , "--task_id", str(self.get_task().get_id())
            , "--stdout", log_file_name
            , "--stderr", "STDOUT"
        ]
        if log.get_logging_debug():
            cmd.append("--debug")
        if not os.path.exists(os.path.dirname(log_file_name)):
            os.mkdir(os.path.dirname(log_file_name))
        self.__subprocess__ = subprocess.Popen(cmd)
        # give the Task a chance to start; 
        # this prevents lots of false starts due to unavailable resources
        # that only are only unavailable to future tasks once this task has kicked off.
        time.sleep(2)
    
    def is_running(self):
        if self.__subprocess__ == None:
            # not even started yet
            return False
        return self.__subprocess__.poll() == None
    def get_exit_status(self):
        if self.__subprocess__ == None:
            # not even started yet
            return None
        return self.__subprocess__.returncode
    def get_pid(self):
        return self.__subprocess__.pid
    
    def interrupt(self):
        """Interrupt this Task"""
        assert not self.__subprocess__ == None, "Cannot interrupt process not started"
        # A bit of interpretive dance to get this to replicate what's much easier in the 2.6 version
        if self.is_running():
            # task is still running; interrupt it! 
            # TODO kill it? (would be signal.SIGKILL)
            log.info("sending SIGINT to pid:%s, task:%s" % (self.get_pid(), self.get_task().get_id()))
            os.kill(self.get_pid(), signal.SIGINT)
        elif self.get_exit_status():
            raise Exception("Task cannot be interrupted. It has already succeeded.")
        else:
            raise Exception("Task cannot be interrupted. It has failed with status %s." % (self.get_exit_status()))

class ForkingNorcDaemon(NorcDaemon):
    
    __log_dir__ = None
    __running_tasks__ = None
    
    def __init__(self, region, poll_frequency, log_dir, redirect_daemon_log):
        #import subprocess
        NorcDaemon.__init__(self, region, poll_frequency)
        self.__log_dir__ = log_dir
        self.__running_tasks__ = []
        daemon_id_for_log = None
        if redirect_daemon_log:
            daemon_id_for_log = self.get_daemon_status().get_id()
        self.__logger__ = ThreadedTaskLogger(log_dir, daemon_id_for_log, False)# only daemon output; don't buffer
    
    def get_name(self):
        """Return a name for this daemon implementation"""
        return 'norcd (forking)'
    def __add_running_task__(self, running):
        self.__running_tasks__.append(running)
    def _get_task_label(self, running_task):
        return "%s:%s" % (running_task.get_task().get_job(), running_task.get_task().get_name())
    def get_running_tasks(self):
        """Returns list of currently running RunnableTask's"""
        running_tasks = []
        to_cleanup = []
        for running_task in self.__running_tasks__:
            if running_task.is_running():
                running_tasks.append(running_task)
            else:
                to_cleanup.append(running_task)
                # no longer running; log that fact for convenience
                exit_status = running_task.get_exit_status()
                if exit_status == 0:
                    log.info("\"%s\" succeeded" % (self._get_task_label(running_task)))
                elif exit_status == 130:
                    log.info("\"%s\" timed out." % (self._get_task_label(running_task)))
                elif exit_status == 131:
                    log.info("\"%s\" was interrupted." % (self._get_task_label(running_task)))
                elif exit_status == 132:
                    log.info("\"%s\" was killed." % (self._get_task_label(running_task)))
                elif exit_status == 133:
                    log.info("\"%s\" did not run." % (self._get_task_label(running_task)))
                elif exit_status == 134:
                    log.info("\"%s\" ended without a status." % (self._get_task_label(running_task)))
                elif exit_status == 127:
                    raise Exception("\"%s\" failed b/c of internal error.  \
TaskInProcess.RUN_TASK_EXE '%s' could not be found! BAD!" % (self._get_task_label(running_task) \
                                , TaskInProcess.RUN_TASK_EXE))
                elif exit_status == 126:
                    raise Exception("\"%s\" failed b/c of internal error.  \
TaskInProcess.RUN_TASK_EXE '%s' is not executable! BAD!" % (self._get_task_label(running_task) \
                                , TaskInProcess.RUN_TASK_EXE))
                else:
                    log.info("\"%s\" failed with exit status %s!" % (self._get_task_label(running_task) \
                        , exit_status))
        
        for no_longer_running in to_cleanup:# TODO can this be done in one loop?
            self.__running_tasks__.remove(no_longer_running)
        
        return running_tasks
    def start_task(self, task, iteration):
        log.info("\"%s:%s\" starting in new process" % (task.get_job().get_name(), task.get_name()))
        tp = TaskInProcess(task, iteration, self.get_daemon_status(), self.__log_dir__)
        tp.run()
        self.__add_running_task__(tp)
    
    def run(self):
        try:
            self.__logger__.start_redirect()
            ended_gracefully = NorcDaemon.run(self)
            self.__logger__.stop_redirect()
            return ended_gracefully
        except Exception, e:
            log.error("Error running daemon!", e)
            return False
        except:
            log.error("Error running daemon & it was poorly thrown!", e)
            return False

class TaskInThread(RunnableTask, threading.Thread):
    
    __logger__ = None
    
    def __init__(self, task, iteration, daemon_status, logger):
        self.__logger__ = logger
        RunnableTask.__init__(self, task, iteration, daemon_status)
        threading.Thread.__init__(self)
    
    def run(self):
        try:
            try:
                self.get_task().do_run(self.get_iteration(), self.get_daemon_status())
            except Exception, e:
                log.error("Exception propegated from task.do_run(). BAD! Bug?", e)
            except:
                log.error("Poorly thrown exception propegated from task.do_run(). BAD! Bug?")
                traceback.print_exc()
        finally:
            self.__logger__.close_log(self.get_task()) # TODO this feels hacky!
    
    def interrupt(self):
        """
        Cannot interrupt the Task thread, but can set it as ended on error.
        (Man, I wish I could interrupt threads in Python!)
        """
        self.get_task().set_ended_on_error(self.get_iteration(), self.get_daemon_status().get_region())
        # a small hack to log in the correct format, but whatever.
        msg = log.__format_msg__("ERROR", "Task was interrupted by the daemon! Sorry.\n", False, 0)
        self.__logger__.write_to_task_log(self.get_task(), msg)

class ThreadingNorcDaemon(NorcDaemon):
    
    __logger__ = None
    
    def __init__(self, region, poll_frequency, log_dir, redirect_daemon_log):
        NorcDaemon.__init__(self, region, poll_frequency)
        daemon_id_for_log = None
        if redirect_daemon_log:
            daemon_id_for_log = self.get_daemon_status().get_id()
        self.__logger__ = ThreadedTaskLogger(log_dir, daemon_id_for_log, True)
    
    def get_name(self):
        """Return a name for this daemon implementation"""
        return 'TMSD (threading)'
    def get_running_tasks(self):
        """Returns list of currently running RunnableTask's"""
        task_threads = []
        for a_thread in threading.enumerate():
            # this list includes all threads including this one; filter it.
            if type(a_thread) == TaskInThread:
                task_threads.append(a_thread)
        return task_threads
    
    def start_task(self, task, iteration):
        """Start the given Task in the given Iteration"""
        log.info("\"%s:%s\" starting in new thread" % (task.get_job().get_name(), task.get_name()))
        tt = TaskInThread(task, iteration, self.get_daemon_status(), sys.stdout)
        tt.start()
    
    def run(self):
        try:
            self.__logger__.start_redirect()
            ended_gracefully = NorcDaemon.run(self)
            self.__logger__.stop_redirect()
            return ended_gracefully
        except Exception, e:
            log.error("Error running daemon!", e)
            return False
        except:
            log.error("Error running daemon & it was poorly thrown!", e)
            return False

