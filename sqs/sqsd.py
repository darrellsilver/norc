#!/usr/bin/python

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
from norc.core import models as norc_models

from norc.utils import log
log = log.Log(settings.LOGGING_DEBUG)

#
#
#

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
    region = norc_models.ResourceRegion.get(options.queue_name)
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
    
    daemon = ForkingSQSDaemon(region, options.poll_frequency, settings.NORC_LOG_DIR
        , not options.no_log_redirect, max_to_run=options.max_to_run)
    
    ended_gracefully = daemon.run()
    if ended_gracefully:
        sys.exit(0)
    else:
        sys.exit(137)

if __name__ == '__main__':
    main()

#
