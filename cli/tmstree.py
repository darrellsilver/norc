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
# Print out the tree for a Norc Job
#
#
#Darrell
#05/09/2009
############################################

import sys

from norc.core import models as core
from optparse import OptionParser

from norc.norc_utils import formatting
from norc.norc_utils import log
log = log.Log()

#
#
#

def format_dependency(dep, iteration=None):
    f = "%s -> %s" % (dep.get_dependency_type(), dep.get_parent().get_name())
    if not iteration == None:
        f += " " + format_task_status(dep.get_parent(), iteration, False)
    return f

def format_task_status(task, iteration, show_all_statuses):
    if iteration == None:
        return ""
    if show_all_statuses:
        all_statuses = core.TaskRunStatus.get_all_statuses(task, iteration)
        f = []
        for s in all_statuses:
            f.append("%s ended %s" % (str(s.get_status()), s.get_date_ended()))
        if len(f) == 0:
            f = "(not yet run)"
        else:
            f = str(f)
    else:
        current_run_status = task.get_current_run_status(iteration)
        if current_run_status == None:
            f = "(not yet run)"
        else:
            f = "(%s ended %s)" % (current_run_status.get_status(), current_run_status.get_date_ended())
    return f

def format_job_label(job, iteration=None):
    if iteration == None:
        return job.get_name()
    else:
        return "%s (%s #%s)" % (job.get_name(), iteration.get_status(), iteration.get_id())

def print_task(task, only_remaining=False, iteration=None, show_all_statuses=False, show_resources=False):
    if not iteration == None and task.is_allowed_to_run(iteration):
        print "    %s is ready to run" % (task.get_name())
    else:
        parent_tasks = []
        deps = task.get_parent_dependencies()
        for dep in deps:
            if only_remaining and not iteration == None and dep.is_satisfied(iteration):
                continue
            parent_tasks.append(format_dependency(dep, iteration))
        formatted_task_root = "    %s %s" % (task.get_name(), format_task_status(task, iteration, show_all_statuses))
        print formatted_task_root
        if len(deps) > 0:
            print "       Depends on %s Tasks:" % (len(deps))
            for pt in parent_tasks:
                print "        %s" % (pt)
        if core.SchedulableTask in task.__class__.__bases__:
            print "       Runs on schedule: %s" % (task.get_pretty_schedule())
    if show_resources and task.resource_relationships.all().count() > 0:
        print "       Demands %s Resource(s):" % (task.resource_relationships.all().count())
        for rr in task.resource_relationships.all():
            print "        %s %s" % (rr.get_units_demanded(), rr.resource)
    #

def print_job(job, only_remaining, iteration=None, show_all_statuses=False, show_resources=False):
    print format_job_label(job, iteration)
    for task in job.get_tasks():
        if only_remaining and not iteration == None:
            status = task.get_current_run_status(iteration)
            if not status == None and status.is_finished():
                continue
        print_task(task, only_remaining, iteration, show_all_statuses, show_resources)

def print_job_iterations(job, exclude_iter_statuses):
    print format_job_label(job)
    for iteration in get_iterations(job, exclude_iter_statuses):
        print "   %s: %s %s - %s" % (iteration.get_id(), iteration.get_status() \
            , iteration.get_date_started(), iteration.get_date_ended())

def print_jobs(jobs, exclude_iter_statuses):
    f = []
    f.append(['Job', 'Open Iters', 'Date Added'])
    f.append(['-','-','-'])
    for job in jobs:
        open_iters = get_iterations(job, exclude_iter_statuses)
        open_iters_str = '-'
        if len(open_iters) > 0:
            open_iters_str = []
            for open_iter in open_iters:
                open_iters_str.append("%s #%s" % (str(open_iter.get_status()), int(open_iter.get_id())))
        f.append([job.get_name(), open_iters_str, job.date_added])
    formatting.pprint_table(sys.stdout, f)
#
#
#

def get_iterations(job, exclude_statuses=None):
    iters = core.Iteration.objects
    iters = iters.filter(job=job)
    if exclude_statuses:
        iters = iters.exclude(status__in=exclude_statuses)
    return iters

def get_jobs(exclude_statuses=None):
    js = core.Job.objects
    if exclude_statuses:
        js = js.exclude(status__in=exclude_statuses)
    return js.all()

def main():
    global task, iteration, region
    parser = OptionParser("%prog --jobs | --job_name <name> \
[--iteration_id <id> | --iterations | --incomplete [--remaining]] \
[--resources] [--all_statuses] [--debug]")
    parser.add_option("--job_name", action="store", help="the name of the job")
    parser.add_option("--jobs", action="store_true", help="list all jobs")
    parser.add_option("--iteration_id", action="store", type="int", help="show status for given iteration id")
    parser.add_option("--iterations", action="store_true", help="show iterations for given job")
    parser.add_option("--incomplete", action="store_true", help="show status of incomplete iterations for this job")
    parser.add_option("--remaining", action="store_true", help="only show tasks that have completed")
    parser.add_option("--all_statuses", action="store_true", help="show all statuses for each task/iteration, not just latest/running")
    parser.add_option("--resources", action="store_true", help="show all resource demands for all tasks")
    parser.add_option("--debug", action="store_true", help="more messages")
    (options, args) = parser.parse_args()
    
    if not options.job_name and not options.jobs:
        raise parser.get_usage()
    if options.remaining and not options.iteration_id:
        raise parser.get_usage()
    
    if options.all_statuses:
        exclude_iter_statuses = []
    else:
        exclude_iter_statuses = ['DONE']
    if options.job_name:
        job = core.Job.get(options.job_name)
    
    show_iterations = []
    if options.iteration_id:
        iteration = core.Iteration.get(options.iteration_id)
        if not iteration.get_job() == job:
            raise Exception("Iteration doesn't match job!")
        show_iterations.append(iteration)
    elif options.incomplete:
        for iteration in get_iterations(job, exclude_iter_statuses):
            show_iterations.append(iteration)
    if options.iterations:
        print_job_iterations(job, exclude_iter_statuses)
    if options.jobs:
        print_jobs(get_jobs(), exclude_iter_statuses)
    elif len(show_iterations) == 0:
        print_job(job, options.remaining, show_resources=options.resources)
    else:
        for iteration in show_iterations:
            print_job(job, options.remaining, iteration, show_all_statuses=options.all_statuses, show_resources=options.resources)
    

if __name__ == '__main__':
    main()

#
