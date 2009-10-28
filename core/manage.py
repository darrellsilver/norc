

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
#    from when they were added to TMS (using the 'date_added' column).
#  - If is_ephemeral is True, the task will be 
#    marked as 'expired' after being run exactly one time.
#    This is regardless of success or failure, and a task 
#    that is retried after failure doesn't lose its position in the queue
#
# TODO Missing basics:
# - Tasks need unique names -- is that true??
# - Tasks should be assigned permissions, runtime environments
#
# TODO Jobs:
# - A Task that is a SchedulableTask needs to have BOTH its predecessors successfully completed and it's run time occur.
#   - The Job can decide whether a SchedulableTask that has missed a run time is to be 
#     caught up fully, latest, or waits its next run time. (see --catch_up option)
# TODO There should be an option to 'catch up' on tasks that should have run but didn't:
#  "--catch_up ALL" to run() all missed occurances of all Tasks that should have run but didn't.
#  "--catch_up LATEST" to run() one occurance of all Tasks that should have run bud didn't.
#
# TODO Need global resources: resources shared across all regions
# TODO dynamic resources, like hitting a URL
# TODO delay between resource usages
# TODO Need ability to retry Tasks, N times before failing, and with min delay between attempts
# TODO Input/Output Job definitions to XML; it's a config, after all.
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

#
#
#

def __status_is_finished__(task, iteration):
    status = task.get_current_run_status(iteration)
    return not status == None and status.is_finished()

def end_ephemeral_iterations():
    for iteration in core.Iteration.get_running_iterations():
        if not iteration.is_ephemeral():
            continue
        tasks = iteration.get_job().get_tasks()
        iteration_is_done = True
        for task in tasks:
            if not __status_is_finished__(task, iteration):
                iteration_is_done = False
                break
        if iteration_is_done:
            iteration.set_done()
    #

def get_tasks_allowed_to_run(asof=None, end_completed_iterations=False, max_to_return=None):
    """
    Get all tasks that are allowed to run, regardless of resources available. Includes all interfaces.
    
    TODO Currently this is EXTREMELY expensive to run.  Use max_to_return or beware the sloooowness!
    *Slowness is due to having to independently query for each Task's lastest status and parent's status.
     One approach is to query for statuses, then tasks with no statuses, then merge the two lists.
     But this only satisfies some of the criteria that this slow way uses.
     Another approach: the daemon should ask for one task at a time, like a proper queue.
    """
    if asof == None:# need to do this here and not in arg so it updates w/ each call
        asof = datetime.datetime.utcnow()
    to_run = []#[[Task, Iteration]...]
    for iteration in core.Iteration.get_running_iterations():
        tasks = iteration.get_job().get_tasks()
        iteration_is_done = True
        for a_task in tasks:
            try:
                if not max_to_return == None and len(to_run) >= max_to_return:
                    break
                elif a_task.is_allowed_to_run(iteration, asof=asof):
                    to_run.append([a_task, iteration])
                    iteration_is_done = False
                elif iteration_is_done and end_completed_iterations and not __status_is_finished__(a_task, iteration):
                    iteration_is_done = False
            except Exception, e:
                log.error("Could not check if task type '%s' is due to run. Skipping.  \
                        BAD! Maybe DB is in an inconsistent state or software bug?" 
                        % (a_task.__class__.__name__), e)
        
        # TODO there's a bug here! iterations end when tasks are sittign in failed state
        if iteration_is_done and end_completed_iterations and iteration.is_ephemeral():
            # this iteration has completed and should be set as such
            iteration.set_done()
        if not max_to_return == None and len(to_run) >= max_to_return:
            break
    
    return to_run

#
