
#
# Copyright (c) 2009, Perpetually.com, LLC.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without modification, 
# are permitted provided that the following conditions are met:
# 
#     * Redistributions of source code must retain the above copyright notice, 
#       this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright notice, 
#       this list of conditions and the following disclaimer in the documentation 
#       and/or other materials provided with the distribution.
#     * Neither the name of the Perpetually.com, LLC. nor the names of its 
#       contributors may be used to endorse or promote products derived from 
#       this software without specific prior written permission.
#     * 
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. 
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, 
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT 
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR 
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, 
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
# POSSIBILITY OF SUCH DAMAGE.
#



############################################
#
#
# Base Task interface and other models
#
#
#
#
#Darrell
#03/31/2009
############################################

import os, datetime, pickle

from django.db import models

from norc import settings
from norc.core.daemons import NorcDaemonStatus, ForkingNorcDaemon

from norc.utils import log
log = log.Log()

#
#
#

class SQSTaskRunStatus(models.Model):
    """A collection of Tasks across which dependencies can be defined."""
    
    STATUS_SKIPPED = 'SKIPPED'     # Task has been skipped; it ran and failed or did not run before being skipped
    STATUS_RUNNING = 'RUNNING'     # Task is running now.. OMG exciting!
    STATUS_ERROR = 'ERROR'         # Task ran but ended in error
    STATUS_TIMEDOUT = 'TIMEDOUT'   # Task timed out while running
    STATUS_CONTINUE = 'CONTINUE'   # Task ran, failed, but children are allowed to run as though it succeeded or children were flow dependencies
    STATUS_RETRY = 'RETRY'         # Task has been asked to be retried
    STATUS_SUCCESS = 'SUCCESS'     # Task ran successfully. Yay!
    
    ALL_STATUSES = (STATUS_SKIPPED, STATUS_RUNNING, STATUS_ERROR
                    , STATUS_CONTINUE, STATUS_TIMEDOUT
                    , STATUS_RETRY, STATUS_SUCCESS)
    
    class Meta:
        db_table = "norc_sqstaskrunstatus"
    
    queue_name = models.CharField(max_length=128)
    task_id = models.PositiveIntegerField()
    status = models.CharField(choices=(zip(ALL_STATUSES, ALL_STATUSES)), max_length=16)
    date_enqueued = models.DateTimeField()
    date_started = models.DateTimeField(blank=True, null=True)
    date_ended = models.DateTimeField(blank=True, null=True)
    controlling_daemon = models.ForeignKey(NorcDaemonStatus, blank=True, null=True)
    
    def get_id(self):
        return self.id
    def get_task_id(self):
        return self.task_id
    def get_status(self):
        return self.status
    def was_successful(self):
        return self.get_status() == SQSTaskRunStatus.STATUS_SUCCESS
    
    def __unicode__(self):
        return u"%s" % (self.get_name())
    def __str__(self):
        return str(self.__unicode__())
    __repr__ = __str__

class SQSTask(object):
    
    date_enqueued = None
    current_run_status = None
    
    def __init__(self, date_enqueued):
        self.date_enqueued = date_enqueued
        self.current_run_status = None
    
    def __set_run_status(self, status, tmsd_status=None):
        assert status in SQSTaskRunStatus.ALL_STATUSES, "Unknown status '%s'" % (status)
        if self.current_run_status == None:
            self.current_run_status = SQSTaskRunStatus(queue_name=self.get_queue_name()
                , task_id=self.get_id()
                , status=status
                , date_enqueued=self.get_date_enqueued())
        else:
            self.current_run_status.status = status
        if status == SQSTaskRunStatus.STATUS_RUNNING:
            self.current_run_status.date_started = datetime.datetime.utcnow()
        else:
            self.current_run_status.date_ended = datetime.datetime.utcnow()
        if not tmsd_status == None:
            self.current_run_status.controlling_daemon = tmsd_status
        self.current_run_status.save()
    def set_ended_on_error(self):
        self.__set_run_status(SQSTaskRunStatus.STATUS_ERROR)
    def set_ended_on_timeout(self):
        self.__set_run_status(SQSTaskRunStatus.STATUS_TIMEDOUT)
    def get_current_run_status(self):
        return self.current_run_status
    
    def do_run(self, tmsd_status):
        """What's actually called by the daemon to run the Message. Don't override!"""
        try:
            try:
                self.__set_run_status(SQSTaskRunStatus.STATUS_RUNNING, tmsd_status=tmsd_status)
                log.info("Running SQS Task '%s'" % (self))
                success = self.run()
                if success:
                    self.__set_run_status(SQSTaskRunStatus.STATUS_SUCCESS)
                    log.info("SQS Task '%s' succeeded.\n\n" % (self))
                else:
                    raise Exception("SQS Task returned failure status. See log for details.")
            except SystemExit, se:
                # in python 2.4, SystemExit extends Exception, this is changed in 2.5 to 
                # extend BaseException, specifically so this check isn't necessary. But
                # we're using 2.4; upon upgrade, this check will be unecessary but ignorable.
                raise se
            except Exception, e:
                log.error("SQS Task failed!", e)
                log.error("\n\n", noalteration=True)
                self.__set_run_status(SQSTaskRunStatus.STATUS_ERROR)
            except:
                # if the error thrown doesn't use Exception(...), ie just throws a string
                log.error("Task failed with poorly thrown exception!")
                traceback.print_exc()
                log.error("\n\n", noalteration=True)
                self.__set_run_status(SQSTaskRunStatus.STATUS_ERROR)
        finally:
            pass
    
    def get_log_file(self):
        #f = "%s.%s" % (self.get_id(), self.get_date_enqueued().strftime('%Y%m%d_%H%M%S'))
        fp = os.path.join(settings.NORC_LOG_DIR, self.get_queue_name(), str(self.get_id()))
        return fp
    def get_date_enqueued(self):
        return self.date_enqueued
    def get_id(self):
        raise NotImplementedError
    def get_queue_name(self):
        raise NotImplementedError
    def has_timeout(self):
        raise NotImplementedError
    def get_timeout(self):
        raise NotImplementedError
    def run(self):
        """
        Run this SQS Task!
        Daemon records success/failure, but any more detail than that is left 
        to the internals of the run() implementation.
        """
        raise NotImplementedError
    
    def __unicode__(self):
        return u"id:%s" % (self.get_id())
    def __str__(self):
        return str(self.__unicode__())
    __repr__ = __str__
#
#
#

def get_sqs_task_class(queue_name):
    # TODO poor hard coding!
    if queue_name in settings.AWS_SQS_ARCHIVE_QUEUES.values():
        from permalink.norc_impl.models import SQSArchiveRequest
        return SQSArchiveRequest
    if queue_name == settings.AWS_SQS_PUBLISH_RECORD:
        from permalink.norc_impl.models import SQSPublishRecord
        return SQSPublishRecord
    if queue_name == settings.AWS_SQS_BROWSER_PUBLISH:
        from permalink.norc_impl.models import SQSBrowserPublish
        return SQSBrowserPublish
    raise Exception("unknown queue_name '%s'.  Configure it in get_sqs_task_class()" \
        % (queue_name))

def get_task(boto_message, queue_name):
    task_class = get_sqs_task_class(queue_name)
    d = pickle.loads(boto_message.get_body())
    if d.has_key('current_run_status'):
        d.pop('current_run_status')
    t = task_class(**d)
    return t
    

class SQSTaskInProcess(object):
    
    RUN_TASK_EXE = 'sqsd_run_task'
    
    __daemon_status__ = None
    __log_dir = None
    __subprocess = None
    
    def __init__(self, daemon_status, log_dir):
        self.__daemon_status__ = daemon_status
        self.__log_dir = log_dir
    
    def get_daemon_status(self):
        return self.__daemon_status__
    
    def run(self):
        cmd = [SQSTaskInProcess.RUN_TASK_EXE
            , "--daemon_status_id", str(self.get_daemon_status().get_id())
            , "--queue_name", str(self.get_daemon_status().region)
            , "--stdout", "DEFAULT"
            , "--stderr", "STDOUT"
        ]
        if log.get_logging_debug():
            cmd.append("--debug")
        #log.info(cmd)
        self.__subprocess = subprocess.Popen(cmd)
        time.sleep(2)
    
    def is_running(self):
        if self.__subprocess == None:
            # not even started yet
            return False
        return self.__subprocess.poll() == None
    def get_exit_status(self):
        if self.__subprocess == None:
            # not even started yet
            return None
        return self.__subprocess.returncode
    def get_pid(self):
        if self.__subprocess == None:
            # not even started yet
            return None
        return self.__subprocess.pid
    
    def interrupt(self):
        """Interrupt this Task"""
        assert not self.__subprocess == None, "Cannot interrupt process not started"
        # A bit of interpretive dance to get this to replicate what's much easier in the 2.6 version
        if self.is_running():
            # task is still running; interrupt it! 
            # TODO kill it? (would be signal.SIGKILL)
            log.info("sending SIGINT to pid:%s" % (self.get_pid()))
            os.kill(self.get_pid(), signal.SIGINT)
        elif self.get_exit_status():
            raise Exception("Task cannot be interrupted. It has already succeeded.")
        else:
            raise Exception("Task cannot be interrupted. It has failed with status %s." % (self.get_exit_status()))
    
    def __unicode__(self):
        return u"SQSTaskInProcess pid:%s running:%s exit_status:%s" \
            % (self.get_pid(), self.is_running(), self.get_exit_status())
    def __str__(self):
        return str(self.__unicode__())
    __repr__ = __str__


class ForkingSQSDaemon(ForkingNorcDaemon):
    # TODO this inheritence is a little lazy; mostly the silly part is that 'region' here means 'queue_name'
    
    __max_to_run__ = None
    __queue__ = None
    __queue_size__ = 0
    __runs_since_queue_size_check__ = 0
    
    def __init__(self, *args, **kwargs):
        self.__max_to_run__ = kwargs['max_to_run']
        kwargs.pop('max_to_run')
        ForkingNorcDaemon.__init__(self, *args, **kwargs)
        c = SQSConnection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
        self.__queue__ = c.get_queue(self.get_queue_name())
    
    def get_name(self):
        return 'SQS Forking Daemon'
    def get_queue_name(self):
        return self.get_daemon_status().region.get_name()# could also look in queue
    def get_max_to_run(self):
        return self.__max_to_run__
    def get_queue(self):
        return self.__queue__
    def __get_task_label__(self, running_task):
        return "pid:%s" % (running_task.get_pid())
    def start_task(self):
        log.info("Starting the next SQS Task in new process")
        tp = SQSTaskInProcess(self.get_daemon_status(), self.__log_dir)
        tp.run()
        self.__add_running_task__(tp)
    
    def run_batch(self):
        num_running = self.get_num_running_tasks()
        max_to_run = self.get_max_to_run()
        # Checking queue size is somewhat expensive and slow. 
        # So if queue is big assume there's tasks to run and only recheck size occasionally
        if self.__runs_since_queue_size_check__ > 10 or self.__queue_size__ < max_to_run*10:
            queue = self.get_queue()
            if queue == None:
                raise Exception("No queue by name '%s'" % (self.get_queue_name()))
            try:
                self.__queue_size__ = queue.count()
            except Exception, e:
                # allow for some shity error w/in SQS (BotoServerError, sslerror, ...)
                log.error("Error getting queue size from SQS. Skipping.", e)
                return
            
            self.__runs_since_queue_size_check__ = 0
        else:
            self.__runs_since_queue_size_check__ += 1
        while num_running < max_to_run and self.__queue_size__ > 0:
            if self.__break_tasks_to_run_loop__:
                # some other thread (request_stop) doesn't want me to continue.  Stop here.
                break
            self.start_task()
            num_running = self.get_num_running_tasks()
            self.__queue_size__ -= 1



#
