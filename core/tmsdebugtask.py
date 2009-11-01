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



############################################
#
# Simple facility for running a single task, unthreaded, 
# and log to stdout/stderr.
#
# This is really a debug tool for testing Tasks,
# and should be used sparingly.
#
#
#
#Darrell
#04/22/2009
############################################

from optparse import OptionParser

from norc.core import models as tms_models
from norc.core import manage as tms_manage
from norc import settings

from norc.utils import log
log = log.Log(settings.LOGGING_DEBUG)

#
#
#

def get_task(task_name, asof=None):
    to_run = tms_manage.get_tasks_due_to_run(asof=asof)
    for task in to_run:
        if task.get_name() == task_name:
            return task
    raise Exception("Unknown Task '%s'" % (task_name))

def __find_iteration__(job):
    iterations = tms_models.Iteration.objects.filter(job=job)
    if iterations.count() == 0:
        raise Exception("Cannot determine iteration for Job '%s'!" % (job))
    elif iterations.count() == 1:
        iteration = iterations[0]
    else:
        iterations = iterations.exclude(status=tms_models.Iteration.STATUS_DONE)
        if iterations.count() == 0:
            raise Exception("Cannot determine iteration for Job '%s'!" % (job))
        else:
            iteration = iterations.latest('date_started')
    return iteration
        

def run_task(task, region_name=None, region=None, iteration=None):
    assert not region_name == None or not region == None, "Must supply either region or region_name"
    tmsd_status = None
    try:
        if region == None:
            region = tms_models.ResourceRegion.get(region_name)
        if region == None:
            raise Exception("Unknown region '%s'" % (region))
        if iteration == None:
            iteration = __find_iteration__(task.get_job())
        tmsd_status = tms_models.NorcDaemonStatus.create(region)
        task.do_run(iteration, tmsd_status)
    finally:
        if not tmsd_status == None:
            tmsd_status.set_status(tms_models.NorcDaemonStatus.STATUS_ENDEDGRACEFULLY)
    return True

def main():
    parser = OptionParser("%prog --task_name <name> --region <regionname> [--debug]")
    parser.add_option("--task_name", action="store", help="the task to run")
    parser.add_option("--region", action="store", help="run the task in this region")
    parser.add_option("--debug", action="store_true", help="more messages")
    (options, args) = parser.parse_args()
    
    if not options.task_name or not options.region:
        raise parser.get_usage()
        
    if options.debug:
        log.set_logging_debug(options.debug)
    
    task = get_task(options.task_name)
    run_task(task, region_name=options.region)
    
    return True

if __name__ == '__main__':
    main()


#
