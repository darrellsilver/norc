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


"""Runs a single task.  Used internally if forking is activated."""

import sys, os, signal
import traceback
from optparse import OptionParser

from norc.core import models as core
from norc.core import report
from norc.utils import log, parsing
log = log.Log()

def _handle_signal(sig_name, exit_code):
    global task, iteration, region, sys
    
    if task == None or iteration == None or region == None:
        log.error("\n", noalteration=True)
        log.error("Received %s but Task not started yet. " + 
            "Stopping with exit code %s." % (sig_name, exit_code))
        log.error("\n", noalteration=True)
    else:
        log.error("\n", noalteration=True)
        log.error("Received %s! Norc Stopping Task with exit code %s." %
            (sig_name, exit_code))
        log.error("\n", noalteration=True)
        task.set_ended_on_error(iteration, region)
    
    # We call the normal os.exit(), even though it trusts that whatever
    # try: ... except block is currently executing will propegate the
    # SystemExit exception instead of handling it. In Python 2.5 SystemExit
    # does not extend Exception so only when catching all (try: ... except:)
    # would this be a problem.  But we're using Python 2.4, so *all* catchers
    # of Exception need to distinguish between Exception & SystemExit
    sys.exit(exit_code)

def _handle_SIGINT(signum, frame):
    assert signum == signal.SIGINT, "This signal handler only handles SIGINT, not '%s'. BUG!" % (signum)
    _handle_signal('SIGINT', 131)

def _handle_SIGTERM(signum, frame):
    assert signum == signal.SIGTERM, "This signal handler only handles SIGTERM, not '%s'. BUG!" % (signum)
    _handle_signal('SIGTERM', 132)

signal.signal(signal.SIGINT, _handle_SIGINT)
signal.signal(signal.SIGTERM, _handle_SIGTERM)

# So they can be seen by the signal handler.
task = None
iteration = None
region = None

def _run_task(task, iteration, daemon_status):
    # sanity check that this Task is allowed to run
    if not task.is_active():
        raise Exception("Cannot run task '%s' b/c it does not need to be run!" % (task))
    # run the Task!
    try:
        task.do_run(iteration, daemon_status)
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
    global task, iteration, region
    parser = OptionParser("%prog -d <daemon_id> -i <iteration_id> "+
        "-l <task_lib> -t <task_id> [--nice 5] [--stdout <file_name>] [--stderr <file_name>|STDOUT>] [--debug]")
    parser.add_option("-d", "--daemon_status_id", action="store", type="int"
        , help="The id of the daemon status that launched this Task")
    parser.add_option("-i", "--iteration_id", action="store", type="int"
        , help="The id of the iteration in which this Task runs")
    parser.add_option("-l", "--task_library", action="store", type="string"
        , help="The path of the Task 'library', e.g.: norc.core.models.RunTask.")
    parser.add_option("-t", "--task_id", action="store", type="string"
        , help="The id of this Task in this library")
    parser.add_option("-n", "--nice", action="store", type="int", default=5
        , help="nice this process. defaults to 5.")
    parser.add_option("--stdout", action="store", type="string"
        , help="Send stdout to this file")
    parser.add_option("--stderr", action="store", type="string"
        , help="Send stderr to this file, or 'STDOUT' for stdout.")
    parser.add_option("--debug", action="store_true", help="more messages")
    (options, args) = parser.parse_args()
    
    # option parsing
    if not options.daemon_status_id or not options.iteration_id \
        or not options.task_library or not options.task_id:
        sys.exit(parser.get_usage())
    if options.debug:
        log.set_logging_debug(options.debug)
    console_stderr = sys.stderr
    
    if options.stdout:
        sys.stdout = open(options.stdout, 'a')
    if options.stderr:
        if options.stderr == 'STDOUT':
            sys.stderr = sys.stdout
        else:
            sys.stderr = open(options.stderr, 'a')
    if not options.nice == 0:
        os.nice(options.nice)
    
    task_class = parsing.parse_class(options.task_library)
    if not task_class:
        print "No task class: '%s'" % options.task_library
        sys.exit(2)
    task = report.task(task_class, options.task_id)
    if not task:
        print "No task matching: class '%s', id %s" % \
            (task_class, options.task_id)
        sys.exit(2)
    daemon_status = report.nds(options.daemon_status_id)
    if not daemon_status:
        print "No daemon status with id %s." % (options.daemon_status_id)
        sys.exit(2)
    iteration = report.iteration(options.iteration_id)
    if not iteration:
        print "No iteration with id %s." % (options.iteration_id)
        sys.exit(2)
    region = daemon_status.region
    
    try:
        _run_task(task, iteration, daemon_status)
        ending_status = task.get_current_run_status(iteration)
        if not ending_status == None and not ending_status.was_successful():
            # if there's no run status, assume success; resource management
            # may have prevented it from working.
            return False
        return True
    except SystemExit, se:
        # in python 2.4, SystemExit extends Exception, this is changed in
        # 2.5 to extend BaseException, specifically so this check isn't
        # necessary. But we're using 2.4; upon upgrade, this check will be
        # unecessary but ignorable.
        sys.exit(se.code)
    except:
        # need to print out any and all exceptions (even poorly thrown ones)
        # before the output handles are closed.
        print >>console_stderr, "Internal error executing Task! Task's log may have more detail"
        if not sys.stderr == console_stderr:
            # report this to the console
            traceback.print_exc(None, console_stderr)
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    success = main()
    if success:
        sys.exit(0)
    sys.exit(1)

#
