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


"""Reporter is how external modules should access Norc data."""

from norc.core.models import *
from django.core.exceptions import FieldError
from norc.utils import log
#log = log.Log(settings.LOGGING_DEBUG)
log = log.Log()

CLASS_DICT = dict(job=Job,
                  task=Task,
                  resource=Resource,
                  region=ResourceRegion,
                  iteration=Iteration,
                  trs=TaskRunStatus)

def get_object(class_key, **kwargs):
    """Retrieves a database object of the given class and attributes.
    
    class_key is the string that represents the wanted class in CLASS_DICT.
    kwargs are the parameters used to find the object.
    
    """
    
    assert class_key in CLASS_DICT.keys(), "Invalid class key."
    class_ = CLASS_DICT[class_key]
    try:
        return class_.objects.get(**kwargs)
    except class_.DoesNotExist, _:
        return None

def get_job(name):
    get_object('job', name=name)

def get_task(name):
    get_object('task', name=name)

def get_resource():
    pass

def get_region(name):
    get_object('region', name=name)

def get_objects(class_key, include, exclude):

    assert class_key in CLASS_DICT.keys(), "Invalid class key."
    return class_.objects.filter(**include).exclude(**exclude)


def get_tasks(job, include_expired=False):
    """Return all active Tasks in this Job"""
    # That this has to look at all implementations of the Task superclass
    tasks = []
    for tci in TaskClassImplementation.get_all():
        # Wont work if there's a collision across libraries, but that'll be errored by django on model creation
        # when it will demand a related_name for Job FK.  Solution isnt to create a related_name, but to rename lib entirely
        tci_name = "%s_set" % (tci.class_name.lower())
        matches = job.__getattribute__(tci_name)
        matches = matches.exclude(status=Task.STATUS_DELETED)
        if not include_expired:
            matches = matches.exclude(status=Task.STATUS_EXPIRED)
        tasks.extend(matches.all())
    return tasks

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
    for iteration in Iteration.get_running_iterations():
        tasks = get_tasks(iteration.get_job())
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

def __status_is_finished__(task, iteration):
    status = task.get_current_run_status(iteration)
    return not status == None and status.is_finished()
