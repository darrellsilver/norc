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

from optparse import OptionParser

from norc import settings
from norc.core.daemons import ThreadingNorcDaemon, ForkingNorcDaemon
from norc.reporter.reporter import get_object
from norc.utils import log
log = log.Log(settings.LOGGING_DEBUG)

def main():
    parser = OptionParser(
        "%prog region [-t] [-d] [-f <frequency>] [--no_log_redirect]")
    
    parser.add_option(
        "-t", "--threads", action="store_true",
        help="Use threading instead of subprocesses. Note that threads in " +
        "Python cannot be interrupted without killing the daemon!")
    parser.add_option(
        "-f", "--poll_frequency", action="store", default=3, type="int",
        help="The delay in seconds between looking for tasks to run.")
    parser.add_option(
        "--no_log_redirect", action="store_true",
        help="Print daemon logging to sys.stdout & sys.stderr instead " + 
             "of redirecting them to a Norc log file.")
    parser.add_option(
        "-d", "--debug", action="store_true", help="more messages")
    
    (options, args) = parser.parse_args()
    
    if options.debug:
        log.set_logging_debug(options.debug)
    
    if options.poll_frequency < 1:
        raise Exception("--poll_frequency must be >= 1")
    
    if not args:
        sys.exit(parser.get_usage())
    
    # resolve the region
    region = get_object('region', name=args[0])
    if region == None:
        raise Exception("Don't know region '%s'" % (options.region))
    
    # register signal handlers for interrupt (ctl-c) & terminate ($ kill <pid>).
    def __handle_SIGINT(signum, frame):
        assert signum == signal.SIGINT, "This signal handler only handles SIGINT, not '%s'. BUG!" % (signum)
        daemon.request_stop()
    def __handle_SIGTERM(signum, frame):
        assert signum == signal.SIGTERM, "This signal handler only handles SIGTERM, not '%s'. BUG!" % (signum)
        daemon.request_kill()
    signal.signal(signal.SIGINT, __handle_SIGINT)
    signal.signal(signal.SIGTERM, __handle_SIGTERM)
    
    if options.threads:
        # multi-threaded; spawn new threads for new Tasks
        daemon = ThreadingNorcDaemon(region,
                                     options.poll_frequency,
                                     settings.NORC_LOG_DIR,
                                     not options.no_log_redirect)
    else:
        # single-threaded; fork new Tasks
        daemon = ForkingNorcDaemon(region,
                                   options.poll_frequency,
                                   settings.NORC_LOG_DIR,
                                   not options.no_log_redirect)
    
    ended_gracefully = daemon.run()
    if ended_gracefully:
        sys.exit(0)
    elif options.threads:
        # there's no way in python to interrupt threads; so gotta force 'em.
        # exit code is 137 on OS X
        os.kill(os.getpid(), signal.SIGKILL)
    else:
        sys.exit(137)

if __name__ == '__main__':
    main()
#
