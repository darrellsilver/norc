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


"""External modules should access Norc data using these functions."""

from norc.core.models import *

DAEMON_STATUS_DICT = {}
DAEMON_STATUS_DICT['running'] = [NorcDaemonStatus.STATUS_RUNNING]
DAEMON_STATUS_DICT['active'] = [NorcDaemonStatus.STATUS_STARTING,
                                NorcDaemonStatus.STATUS_RUNNING,
                                NorcDaemonStatus.STATUS_PAUSEREQUESTED,
                                NorcDaemonStatus.STATUS_STOPREQUESTED,
                                NorcDaemonStatus.STATUS_KILLREQUESTED,
                                NorcDaemonStatus.STATUS_PAUSED,
                                NorcDaemonStatus.STATUS_STOPINPROGRESS,
                                NorcDaemonStatus.STATUS_KILLINPROGRESS]
DAEMON_STATUS_DICT['errored'] = [NorcDaemonStatus.STATUS_ERROR]
DAEMON_STATUS_DICT['interesting'] = []
DAEMON_STATUS_DICT['interesting'].extend(DAEMON_STATUS_DICT['active'])
DAEMON_STATUS_DICT['interesting'].extend(DAEMON_STATUS_DICT['errored'])
DAEMON_STATUS_DICT['all'] = NorcDaemonStatus.ALL_STATUSES

def get_object(class_, **kwargs):
    """Retrieves a database object of the given class and attributes.
    
    class_ is the class of the object to find.
    kwargs are the parameters used to find the object.get_daemon_status
    If no object is found, returns None.
    
    """
    try:
        return class_.objects.get(**kwargs)
    except class_.DoesNotExist, dne:
        return None

def get_job(name):
    return get_object(Job, name=name)

def get_task(class_, id):
    return get_object_from_class(class_, id=id)

def get_region(name):
    return get_object(ResourceRegion, name=name)

def get_iteration(id):
    return get_object(Iteration, id=id)

def get_nds(id):
    return get_object(NorcDaemonStatus, id=id)

def get_daemon_statuses(since_date=None, status_filter='all'):
    nds_query = NorcDaemonStatus.objects.all()
    if since_date != None:
        nds_query = nds_query.exclude(date_ended__lte=since_date)
    if status_filter != 'all' and status_filter in DAEMON_STATUS_DICT:
        include_statuses = DAEMON_STATUS_DICT[status_filter.lower()]
        nds_query = nds_query.filter(status__in=include_statuses)
    return nds_query

# def get_task_statuses(status_filter='all'):
#     if status_filter == 'all':
#         TaskRunStatus.objects.all()
#     else:
#         include_statuses = TASK_STATUS_DICT[status_filter.lower()]
#         return TaskRunStatus.objects.filter(status__in=include_statuses)

