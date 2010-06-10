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



##################################################
#
# Set status of TMS tasks
#
#
#
#
#Darrell
#06/27/2009
##################################################

import sys
from optparse import OptionParser

from norc.core import models as core
from norc.utils import log

log = log.Log()

def format_job_label(job, iteration=None):
    if iteration == None:
        return job.get_name()
    else:
        return "%s (%s #%s)" % (job.get_name(), iteration.get_status(), iteration.get_id())

def get_iterations(job, exclude_statuses=None):
    iters = core.Iteration.objects
    iters = iters.filter(job=job)
    if exclude_statuses:
        iters = iters.exclude(status__in=exclude_statuses)
    return iters

def print_job_iterations(job):
    print format_job_label(job)
    for iteration in get_iterations(job):
        print "   %s: %s %s - %s" % (iteration.get_id(), iteration.get_status() \
            , iteration.get_date_started(), iteration.get_date_ended())

#
#
#

def determine_status(options):
    if options.skipped:
        return core.TaskRunStatus.STATUS_SKIPPED
    if options.running:
        return core.TaskRunStatus.STATUS_RUNNING
    if options.error:
        return core.TaskRunStatus.STATUS_ERROR
    if options.timedout:
        return core.TaskRunStatus.STATUS_TIMEDOUT
    if options.continue_anyway:
        return core.TaskRunStatus.STATUS_CONTINUE
    if options.retry:
        return core.TaskRunStatus.STATUS_RETRY
    if options.success:
        return core.TaskRunStatus.STATUS_SUCCESS
    raise Exception("Unknown status in options %s" % (options))

def as_no(no):
    if no == None:
        return 0
    return 1
def check_status_options(options):
    i = as_no(options.skipped) + as_no(options.running) + as_no(options.error) + as_no(options.timedout) \
        + as_no(options.continue_anyway) + as_no(options.retry) + as_no(options.success)
    if i == 1:
        return True
    return False
def main():
    global task, iteration, region
    parser = OptionParser("%prog --job_name <JOB_NAME> --iteration_id <#> --task_name <TASK_NAME> \
--skipped | --running | --error | --timedout | --continue_anyway | --retry | --success \
[--delete] [--debug]")
    parser.add_option("--job_name", action="store", help="the name of the job")
    parser.add_option("--iteration_id", action="store", type="int", help="iteration id")
    parser.add_option("--task_name", action="store", help="the Task name")
    parser.add_option("--skipped", action="store_true"
        , help="Task has been skipped; it ran and failed or did not run before being skipped")
    parser.add_option("--running", action="store_true", help="Task is running now.. OMG exciting!")
    parser.add_option("--error", action="store_true", help="Task ran but ended in error")
    parser.add_option("--timedout", action="store_true", help="Task timed out while running")
    parser.add_option("--continue_anyway", action="store_true"
        , help="Task ran, failed, but children are allowed to run as though it succeeded or children were flow dependencies")
    parser.add_option("--retry", action="store_true", help="Task has been asked to be retried")
    parser.add_option("--success", action="store_true", help="Task ran successfully. Yay!")
    parser.add_option("--delete", action="store_true", help="Delete this status.")
    parser.add_option("--debug", action="store_true", help="more messages")
    (options, args) = parser.parse_args()
    
    if not options.job_name:
        sys.exit(parser.get_usage())
    if not options.iteration_id:
        sys.exit(parser.get_usage())
    if not check_status_options(options):
        sys.exit(parser.get_usage())
    
    try:
        job = core.Job.get(options.job_name)
    except core.Job.DoesNotExist, dne:
        sys.exit("ERROR: Job '%s' does not exist!" % (options.job_name))
    try:
        iteration = core.Iteration.get(options.iteration_id)
    except core.Iteration.DoesNotExist, dne:
        sys.exit("ERROR: Iteration ID %s does not exist!" % (options.iteration_id))
    if not iteration.get_job() == job:
        print "ERROR: Job doesn't match iteration! Available Iterations:"
        print_job_iterations(job)
        sys.exit(1)
    task = None
    for a_task in job.get_tasks():
        if a_task.get_name().lower() == options.task_name.lower():
            task = a_task
            break
    if task == None:
        sys.exit("ERROR: Task '%s' not found in job %s!" % (options.task_name, job.get_name()))
    
    #
    status = determine_status(options)
    if options.delete:
        trs = core.TaskRunStatus.get_all_statuses(task, iteration)
        if trs == None:
            trs = []
        else:
            trs = trs.filter(status=status)
        if len(trs) >= 1:
            for tr in trs:
                log.info("Deleting status ID %s for %s %s w/ status %s" 
                    % (tr.get_id(), job.get_name(), task.get_name(), status))
                tr.delete()
        else:
            sys.exit("ERROR: There are %s statuses for %s %s w/ status %s" \
                % (len(trs), job.get_name(), task.get_name(), status))
    else:
        log.info("Setting %s %s to %s" % (job.get_name(), task.get_name(), status))
        task.__set_run_status(iteration, status)
    

if __name__ == '__main__':
    main()

#
