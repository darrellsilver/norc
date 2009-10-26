#!/usr/bin/python

########################################
#
# A daemon for running SQS Tasks, similar to tmsd
#
#
#Darrell
#05/25/2009
########################################

import sys, os, time
import signal, subprocess
from optparse import OptionParser

from boto.sqs.connection import SQSConnection

from norc import settings
from norc.bin import tmsd
from norc.core import models as tms_models

from utils import log
log = log.Log(settings.LOGGING_DEBUG)

#
#
#

class SQSTaskInProcess(object):
    
    RUN_TASK_EXE = 'sqsd_run_task'
    
    __daemon_status__ = None
    __log_dir__ = None
    __subprocess__ = None
    
    def __init__(self, daemon_status, log_dir):
        self.__daemon_status__ = daemon_status
        self.__log_dir__ = log_dir
    
    def get_daemon_status(self):
        return self.__daemon_status__
    
    def run(self):
        cmd = [SQSTaskInProcess.RUN_TASK_EXE
            , "--daemon_status_id", str(self.get_daemon_status().get_id())
            , "--queue_name", str(self.get_daemon_status().get_region())
            , "--stdout", "DEFAULT"
            , "--stderr", "STDOUT"
        ]
        if log.get_logging_debug():
            cmd.append("--debug")
        #log.info(cmd)
        self.__subprocess__ = subprocess.Popen(cmd)
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
        if self.__subprocess__ == None:
            # not even started yet
            return None
        return self.__subprocess__.pid
    
    def interrupt(self):
        """Interrupt this Task"""
        assert not self.__subprocess__ == None, "Cannot interrupt process not started"
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


class ForkingSQSDaemon(tmsd.ForkingNorcDaemon):
    # TODO this inheritence is a little lazy; mostly the silly part is that 'region' here means 'queue_name'
    
    __max_to_run__ = None
    __queue__ = None
    __queue_size__ = 0
    __runs_since_queue_size_check__ = 0
    
    def __init__(self, *args, **kwargs):
        self.__max_to_run__ = kwargs['max_to_run']
        kwargs.pop('max_to_run')
        tmsd.ForkingNorcDaemon.__init__(self, *args, **kwargs)
        c = SQSConnection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
        self.__queue__ = c.get_queue(self.get_queue_name())
    
    def get_name(self):
        return 'SQS Forking Daemon'
    def get_queue_name(self):
        return self.get_daemon_status().get_region().get_name()# could also look in queue
    def get_max_to_run(self):
        return self.__max_to_run__
    def get_queue(self):
        return self.__queue__
    def __get_task_label__(self, running_task):
        return "pid:%s" % (running_task.get_pid())
    def start_task(self):
        log.info("Starting the next SQS Task in new process")
        tp = SQSTaskInProcess(self.get_daemon_status(), self.__log_dir__)
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
            self.__queue_size__ = queue.count()
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


def main():
    parser = OptionParser("%prog --queue_name <queue_name> --max_to_run <#> \
[--poll_frequency <3>] [--no_log_redirect] [--debug]")
    parser.add_option("--poll_frequency", action="store", default=3, type="int"
        , help="delay in seconds between looking for tasks to run")
    parser.add_option("--queue_name", action="store", help="queue name this daemon monitors")
    parser.add_option("--max_to_run", action="store", type="int"
        , help="max Tasks that can be run at a time")
    parser.add_option("--no_log_redirect", action="store_true"
        , help="print daemon logging to sys.stdout & sys.stderr instead of redirecting them to a TMS log file.")
    parser.add_option("--debug", action="store_true", help="more messages")
    (options, args) = parser.parse_args()
    
    log.set_logging_debug(options.debug)
    
    if options.poll_frequency < 1:
        raise Exception("--poll_frequency must be >= 1")
    if not options.max_to_run or options.max_to_run < 1:
        raise Exception("--max_to_run must be >= 1. found %s" % (options.max_to_run))
    
    if not options.queue_name:
        sys.exit(parser.get_usage())
    
    # resolve the region
    # currently an SQS Queue is mapped 1:1 to a ResourceRegion
    region = tms_models.ResourceRegion.get(options.queue_name)
    if region == None:
        raise Exception("Don't know region '%s'" % (options.queue_name))
    
    # register signal handlers for interrupt (ctl-c) & terminate ($ kill <pid>).
    def __handle_SIGINT__(signum, frame):
        assert signum == signal.SIGINT, "This signal handler only handles SIGINT, not '%s'. BUG!" % (signum)
        daemon.request_stop()
    def __handle_SIGTERM__(signum, frame):
        assert signum == signal.SIGTERM, "This signal handler only handles SIGTERM, not '%s'. BUG!" % (signum)
        daemon.request_kill()
    signal.signal(signal.SIGINT, __handle_SIGINT__)
    signal.signal(signal.SIGTERM, __handle_SIGTERM__)
    
    daemon = ForkingSQSDaemon(region, options.poll_frequency, settings.TMS_LOG_DIR
        , not options.no_log_redirect, max_to_run=options.max_to_run)
    
    ended_gracefully = daemon.run()
    if ended_gracefully:
        sys.exit(0)
    else:
        sys.exit(137)

if __name__ == '__main__':
    main()

#
