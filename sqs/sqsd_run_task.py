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
# Run a single Task.
#
#
#Darrell
#05/25/2009
############################################

import sys, os, signal
import traceback
from optparse import OptionParser

from boto.sqs.connection import SQSConnection

from norc import settings, sqs
from norc.core.models import NorcDaemonStatus
# from norc.sqs import utils as sqs
# from norc.sqs import models as sqs

from norc.utils import log
log = log.Log()

#
#
#

def __handle_timeout__(*args):
    global task
    sig_name = 'TIMEOUT'
    exit_code = 130
    if task == None:
        log.error("Received %s but Task not started yet. Stopping with exit code %s." % (sig_name, exit_code))
    elif not task.has_timeout():
        raise Exception("Task %s doesn't handle timeouts. How did you get here? BUG!" % (task))
    __handle_signal__(sig_name, exit_code, True)

def __start_timeout_timer__():
    global task
    assert not task == None, "Task is None; timer started out of order. BUG!"
    if not task.has_timeout():
        return False
    signal.alarm(task.get_timeout())
    return True
def __stop_timeout_timer__():
    global task
    assert not task == None, "Task is None; timer stopped but no Task defined. BUG!"
    if not task.has_timeout():
        return False
    signal.alarm(0)
    return True

def __handle_signal__(sig_name, exit_code, timeout):
    global task
    
    if task == None:
        log.error("\n", noalteration=True)
        log.error("Received %s but Task not started yet. Stopping with exit code %s." % (sig_name, exit_code))
        log.error("\n", noalteration=True)
    else:
        log.error("\n", noalteration=True)
        log.error("Received %s! Norc Stopping Task with exit code %s." % (sig_name, exit_code))
        log.error("\n", noalteration=True)
        if timeout:
            task.set_ended_on_timeout()
        else:
            task.set_ended_on_error()
    
    # We call the normal os.exit(), even though it trusts that whatever try: ... except block
    # is currently executing will propegate the SystemExit exception instead of handling it.
    # In Python 2.5 SystemExit does not extend Exception so only when catching all (try: ... except:)
    # would this be a problem.  But we're using Python 2.4, so *all* catchers of Exception need to
    # distinguish between Exception & SystemExit
    sys.exit(exit_code)
def __handle_SIGINT__(signum, frame):
    assert signum == signal.SIGINT, "This signal handler only handles SIGINT, not '%s'. BUG!" % (signum)
    __handle_signal__('SIGINT', 131, False)
def __handle_SIGTERM__(signum, frame):
    assert signum == signal.SIGTERM, "This signal handler only handles SIGTERM, not '%s'. BUG!" % (signum)
    __handle_signal__('SIGTERM', 132, False)

signal.signal(signal.SIGINT, __handle_SIGINT__)
signal.signal(signal.SIGTERM, __handle_SIGTERM__)
signal.signal(signal.SIGALRM, __handle_timeout__)

# So they can be seen by the signal handler
task = None

#
#
#

def __redirect_outputs__(task, stdout, stderr):
    console_stderr = sys.stderr
    if stdout:
        if stdout == 'DEFAULT':
            sys.stdout = open(task.get_log_file(), 'a')
        else:
            sys.stdout = open(stdout, 'a')
    if stderr:
        if stderr == 'STDOUT':
            sys.stderr = sys.stdout
        else:
            sys.stderr = open(stderr, 'a')
    return console_stderr

def __get_daemon_status__(daemon_status_id):
    # get the controlling daemon
    try:
        daemon_status = NorcDaemonStatus.objects.get(id=daemon_status_id)
        return daemon_status
        #if not daemon_status.is_running():
        #    raise Exception("Cannot use daemon '%s'. It is not running!" % (daemon_status))
    except NorcDaemonStatus.DoesNotExist, dne:
        raise Exception("No daemon status by id %s" % (daemon_status_id))

# DEPR
# def __get_task__(boto_message, queue_name):
#     if boto_message == None:
#         return None
#     t = sqs.get_task(boto_message, queue_name)
#     return t

def __run_task__(task, daemon_status):
    # run the Task!
    #queue.delete_message(m)
    try:
        __start_timeout_timer__()
        task.do_run(daemon_status)
        __stop_timeout_timer__()
    except SystemExit, se:
        # in python 2.4, SystemExit extends Exception, this is changed in 2.5 to 
        # extend BaseException, specifically so this check isn't necessary. But
        # we're using 2.4; upon upgrade, this check will be unecessary but ignorable.
        raise se
    except Exception, e:
        log.error("Exception propegated from task.do_run(). BAD! Bug?", e)
        raise e
    except:
        log.error("Poorly thrown exception propegated from task.do_run(). BAD! Bug?")
        traceback.print_exc()
        raise Exception("Poorly handled exception propegated from task.do_run(). BAD! Bug?")
    #

def main():
    global task
    parser = OptionParser("%prog --daemon_status_id <id> --queue_name <queue_name> \
[--nice <0>] [--stdout <file_name|DEFAULT>] [--stderr <file_name>|STDOUT>] [--debug]")
    parser.add_option("--daemon_status_id", action="store", type="int"
        , help="The id of the daemon status that launched this Task")
    parser.add_option("--queue_name", action="store", type="string"
        , help="The name of the queue from which to read")
    parser.add_option("--nice", action="store", type="int", default=0
        , help="nice this process. defaults to 5.")
    parser.add_option("--stdout", action="store", type="string"
        , help="Send stdout to this file, or special value 'DEFAULT' \
sends it a the stream unique to this Task request")
    parser.add_option("--stderr", action="store", type="string"
        , help="Send stderr to this file, or special value 'STDOUT' sends it to stdout")
    parser.add_option("--debug", action="store_true", help="more messages")
    (options, args) = parser.parse_args()
    
    # option parsing
    if not options.daemon_status_id or not options.queue_name:
        sys.exit(parser.get_usage())
    log.set_logging_debug(options.debug)
    
    if not options.nice == 0:
        os.nice(options.nice)
    
    console_stderr = None
    try:
        # DEPR
        # c = SQSConnection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
        # q = c.get_queue(options.queue_name)
        # boto_message = q.read()
        # task = __get_task__(boto_message, options.queue_name)
        task = sqs.pop_task(options.queue_name)
        # task = sqs.pop_task(q)
        if task == None:
            log.debug("No task in queue '%s' pid:%s" % (options.queue_name, os.getpid()))
            sys.exit(133)
        else:
            log.debug("Starting SQS Queue '%s' Task:%s pid:%s" % (options.queue_name, task.get_id(), os.getpid()))
            # q.delete_message(boto_message)
            console_stderr = __redirect_outputs__(task, options.stdout, options.stderr)
            daemon_status = __get_daemon_status__(options.daemon_status_id)
            __run_task__(task, daemon_status)
            ending_status = task.get_current_run_status()
            if ending_status == None:
                sys.exit(134)
            if not ending_status.was_successful():
                sys.exit(1)
    except SystemExit, se:
        # in python 2.4, SystemExit extends Exception, this is changed in 2.5 to 
        # extend BaseException, specifically so this check isn't necessary. But
        # we're using 2.4; upon upgrade, this check will be unecessary but ignorable.
        sys.exit(se.code)
    except:
        # need to print out any and all exceptions (even poorly thrown ones)
        # before the output handles are closed.
        if console_stderr == None:
            print "Internal error executing Task and console_stderr not defined!"
        else:
            print >>console_stderr, "Internal error executing Task! Task's log may have more detail"
        if not sys.stderr == console_stderr:
            # report this to the console
            traceback.print_exc(None, console_stderr)
        traceback.print_exc()
        sys.exit(2)

if __name__ == '__main__':
    main()

