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

from models import *
from django.core.exceptions import FieldError

CLASS_DICT = dict(job=Job,
                  rc=RunCommand,
                  resource=Resource,
                  region=ResourceRegion,
                  iteration=Iteration,
                  trs=TaskRunStatus,
                  nds=NorcDaemonStatus)

DAEMON_STATUS_DICT = {}
DAEMON_STATUS_DICT['running'] = [
    NorcDaemonStatus.STATUS_RUNNING]
DAEMON_STATUS_DICT['active'] = [
    NorcDaemonStatus.STATUS_STARTING,
    NorcDaemonStatus.STATUS_RUNNING,
    NorcDaemonStatus.STATUS_PAUSEREQUESTED,
    NorcDaemonStatus.STATUS_STOPREQUESTED,
    NorcDaemonStatus.STATUS_KILLREQUESTED,
    NorcDaemonStatus.STATUS_PAUSED,
    NorcDaemonStatus.STATUS_STOPINPROGRESS,
    NorcDaemonStatus.STATUS_KILLINPROGRESS]
DAEMON_STATUS_DICT['errored'] = [
    NorcDaemonStatus.STATUS_ERROR]
DAEMON_STATUS_DICT['interesting'] = []
DAEMON_STATUS_DICT['interesting'].extend(
    DAEMON_STATUS_DICT['active'])
DAEMON_STATUS_DICT['interesting'].extend(
    DAEMON_STATUS_DICT['errored'])
DAEMON_STATUS_DICT['all'] = None    # meaning all of them

TASK_STATUS_FILTER_2_STATUS_LIST = {}
TASK_STATUS_FILTER_2_STATUS_LIST['running'] = [TaskRunStatus.STATUS_RUNNING]
TASK_STATUS_FILTER_2_STATUS_LIST['active'] = [TaskRunStatus.STATUS_RUNNING]
TASK_STATUS_FILTER_2_STATUS_LIST['errored'] = [TaskRunStatus.STATUS_ERROR,
                                               TaskRunStatus.STATUS_TIMEDOUT]
TASK_STATUS_FILTER_2_STATUS_LIST['success'] = [TaskRunStatus.STATUS_SUCCESS
                                            , TaskRunStatus.STATUS_CONTINUE]
TASK_STATUS_FILTER_2_STATUS_LIST['interesting'] = []
TASK_STATUS_FILTER_2_STATUS_LIST['interesting'].extend(
    TASK_STATUS_FILTER_2_STATUS_LIST['active'])
TASK_STATUS_FILTER_2_STATUS_LIST['interesting'].extend(
    TASK_STATUS_FILTER_2_STATUS_LIST['errored'])
TASK_STATUS_FILTER_2_STATUS_LIST['all'] = None      # meaning all of them


def get_object(class_key, **kwargs):
    """Retrieves a database object of the corresponding class and attributes.
    
    class_key is a string that represents the desired class in CLASS_DICT.
    kwargs are the parameters used to find the object.
    
    """
    assert class_key in CLASS_DICT.keys(), "Invalid class key."
    return get_object_from_class(CLASS_DICT[class_key], **kwargs)

def get_object_from_class(class_, **kwargs):
    """Retrieves a database object of the given class and attributes.
    
    class_key is the string that represents the wanted class in CLASS_DICT.
    kwargs are the parameters used to find the object.
    
    """
    try:
        return class_.objects.get(**kwargs)
    except class_.DoesNotExist, dne:
        return None

def get_job(name):
    return get_object('job', name=name)

def get_task(class_, id):
    return get_object_from_class(class_, id=id)

def get_region(name):
    return get_object('region', name=name)

def get_iteration(id):
    return get_object('iteration', id=id)

def get_daemon_status(id):
    return get_object('nds', id=id)

def get_objects(class_key, filters={}, excludes={}):
    #assert class_key in CLASS_DICT.keys(), "Invalid class key."
    #class_ = CLASS_DICT[class_key]
    #return class_.objects.filter(**filters).exclude(**excludes)
    pass

def get_daemon_statuses(status_filter='all'):
    include_statuses = DAEMON_STATUS_DICT[status_filter.lower()]
    return get_objects('nds', filters=dict(status__in=include_statuses))

