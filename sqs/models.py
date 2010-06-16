
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
from norc.core.daemons import NorcDaemonStatus

from norc.utils import log
log = log.Log()

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


#
