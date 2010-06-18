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
# Norc task management, runnable from the cmd line
#
# Currently, if a scheduled task is not run on time, 
# it will not catch up.  This behavior is the same as crontab:
# If the host is turned off when a job should run, it never runs.
#
# Norc can be used as a queue service for tasks. 
# The following patterns allow this behavior:
#  - Tasks are always executed on a FIFO basis *for that task implementation*, 
#    from when they were added to Norc (using the 'date_added' column).
#  - If is_ephemeral is True, the task will be 
#    marked as 'expired' after being run exactly one time.
#    This is regardless of success or failure, and a task 
#    that is retried after failure doesn't lose its position in the queue
#
#
# TODO add definition of Norc here
#
# TODO Missing basics:
# - Tasks need unique names -- is that true??
# - Tasks should be assigned permissions, runtime environments
#   - Tasks should belong to 'domains' that restrict the environment in which they run, like 'solaris only'
#
# TODO Jobs:
# - A Task that is a SchedulableTask needs to have BOTH its predecessors successfully completed and it's run time occur.
#   - The Job can decide whether a SchedulableTask that has missed a run time is to be 
#     caught up fully, latest, or waits its next run time. (see --catch_up option)
# TODO There should be an option to 'catch up' on tasks that should have run but didn't:
#  "--catch_up ALL" to run() all missed occurances of all Tasks that should have run but didn't.
#  "--catch_up LATEST" to run() one occurance of all Tasks that should have run bud didn't.
#
# TODO Need ability to run an arbitrary cmd-line script as a Task
# TODO Need Timeout support for all Tasks
# TODO Need global resources: resources shared across all regions
# TODO dynamic resources, like hitting a URL
# TODO delay between resource usages
# TODO Need ability to retry Tasks, N times before failing, and with min delay between attempts
# TODO Generic Task types; command-line, call url, etc
# TODO Input/Output Job definitions to XML; it's a config, after all.
# TODO switch deamon from threading to process forking
#
#
#Darrell
#04/01/2009
############################################

import datetime

from norc.core import models as core
from norc import settings

from norc.utils import log
log = log.Log(settings.LOGGING_DEBUG)

# DEPR
# def end_ephemeral_iterations():
#     for iteration in core.Iteration.get_running_iterations():
#         if not iteration.is_ephemeral():
#             continue
#         tasks = iteration.get_job().get_tasks()
#         iteration_is_done = True
#         for task in tasks:
#             if not __status_is_finished__(task, iteration):
#                 iteration_is_done = False
#                 break
#         if iteration_is_done:
#             iteration.set_done()
