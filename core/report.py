
"""External modules should access Norc data using these functions.

The main benefit currently is to prevent the occurence of a try block
everywhere data is needed, and to reduce the amount of code needed for
retrievals using consistent attributes.  Additionally, it prevents
external modules from having to query core classes directly.

"""

from norc.core.models import *
from norc.core.constants import Status
from norc.norc_utils.parsing import parse_since
from norc.norc_utils.formatting import untitle
from norc.norc_utils.django_extras import get_object

REPORTS = {}

class Report(type):
    """A definition for the data of a status table on the frontend.
    
    Contains all the information needed for retrieving and organizing the
    data for displaying in a table on the status page.
    
    Required parameters:
    
    key         String which identifies this data.
    data        A dictionary whose keys represent columns in the table and
                whose values are functions which take an object and the GET
                dict from the AJAX request and return the desired data.
    
    Optional parameters:
    
    retrieve        Function which returns the basic set of data.  Needed
                    if the data is to have its own table.
    detail_key      String which identifies the type of data that expanding
                    a row in this table will reveal.
    details         Function which takes the ID of an object and the GET
                    params and returns the detail objects for that ID.
    since_filter    Function which takes data and a since date and filters
                    the data using that date.
    order_by        Function which takes data and an optional order string
                    and returns ordered data.
    
    """
    def __new__(cls, name, bases, dct):
        function = type(lambda: None)
        for k, v in dct.iteritems():
            if type(v) == function:
                dct[k] = staticmethod(v)
        for k in dct['headers']:
            k = untitle(k)
            if not k in dct['data']:
                dct['data'][k] = lambda obj, **kws: getattr()
        return type.__new__(cls, name, bases, dct)
    
    def __init__(self, name, bases, dct):
        super(Report, self).__init__(self, name, bases, dct)
        REPORTS[name] = self
        # if base:
        #     self = copy(REPORT[base])
        # for k, v in kwargs.iteritems():
        #     setattr(self, k, v)
        # DATA_DEFS[self.key] = self
    
    def __call__(self, id=None):
        return self.get(id) if id != None else self.get_all()
    
    # def __getattr__(self, *args, **kwargs):
    #     try:
    #         return super(Report, self).__getattr__(self, *args, **kwargs)
    #     except AttributeError:
    #         return None
    

def since_filter(query, since):
    if type(since) == str:
        since = parse_since(since)
    return query.exclude(ended__lt=since) if since else query

date_ended_order = lambda data, o: data.order_by(o if o else '-ended')
date_ended_getter = lambda obj, **kws: obj.ended if obj.ended else '-'

class BaseReport(object):
    """Ideally, this would be replaced with a class decorator in 2.6."""
    __metaclass__ = Report
    get = lambda id: None
    get_all = lambda: None
    details = {}
    headers = []
    data = {}

class daemons(BaseReport):
    
    get = lambda id: get_object(Daemon, id=id)
    get_all = lambda: Daemon.objects.all()
    since_filter = date_ended_since
    order_by = date_ended_order
    
    details = {
        'instances': lambda id, status=None, **kws:
            get(id).instances.status_in(status),
    }
    headers = ['ID', 'Queue', 'Queue Type', 'Host', 'PID', 'Running',
        'Succeeded', 'Failed', 'Status', 'Started', 'Ended']
    data = {
        'queue': lambda daemon, **kws: daemon.queue.name,
        'queue_type': lambda daemon, **kws: daemon.queue.__class__.__name__,
        'running': lambda daemon, since, **kws:
            daemon.instances.since(since).status_in([Status.RUNNING]).count(),
        'succeeded': lambda daemon, since, **kws:
            daemon.instances.since(since).status_in(Status.SUCCEEDED).count(),
        'failed': lambda daemon, since, **kws:
            daemon.instances.since(since).status_in(Status.FAILED).count(),
        'ended': date_ended_getter,
    }
    

class scheduler(BaseReport):
    
    get = lambda id: get_object(Scheduler, id=id)
    get_all = lambda: Scheduler.objects.all()
    
    details = {
        'schedules': lambda id, **kws:
            Schedule.objects.filter(scheduler__id=id)
    }
    headers = ['ID', 'Active', 'Host', 'Heartbeat']
    

class instances(MakeReport):
    
    get = lambda id: get_object(Instance, id=id)
    get_all = lambda: Instance.objects.all()
    since_filter = date_ended_since
    order_by = date_ended_order
    
    headers = ['ID', 'Task', 'Task Type', '']
    data = {}

# DataDefinition(
#     key='tasks',
#     since_filter=date_ended_filter,
#     order_by=date_ended_order,
#     data={
#         'id': lambda trs, _: trs.id,
#         'job': lambda trs, _: trs.task.job.name,
#         'task': lambda trs, _: trs.task.get_name(),
#         'status': lambda trs, _: trs.status,
#         'started': lambda trs, _: trs.date_started,
#         'ended': date_ended_getter,
#     },
# )

# tasks = DataDefinition(
#     key='tasks',
#     since_filter=date_ended_filter,
#     order_by=date_ended_order,
#     data={
#         'id': lambda trs, _: trs.id,
#         'job': lambda trs, _: trs.task.job.name,
#         'iteration': lambda trs, _: trs.iteration.id,
#         'task': lambda trs, _: trs.task.get_name(),
#         'status': lambda trs, _: trs.status,
#         'started': lambda trs, _: trs.date_started,
#         'ended': date_ended_getter,
#     },
# )
# 
# DataDefinition(
#     key='failedtasks',
#     retrieve=lambda: TaskRunStatus.objects.filter(
#         status__in=TaskRunStatus.STATUS_CATEGORIES['errored']),
#     since_filter=tasks.since_filter,
#     order_by=tasks.order_by,
#     data=tasks.data,
# )
# 
# DataDefinition(
#     key='jobs',
#     retrieve=lambda: report.jobs(),
#     detail_key='iterations',
#     details=lambda cid, _: report.iterations(cid),
#     data={
#         'id': lambda job, _: job.id,
#         'name': lambda job, _: job.name,
#         'description': lambda job, _: job.description,
#         'added': lambda job, _: job.date_added,
#     },
# )
# 
# DataDefinition(
#     key='iterations',
#     detail_key='tasks',
#     details=lambda cid, _: report.tasks_from_iter(cid),
#     order_by=date_ended_order,
#     data={
#         'id': lambda i, _: i.id,
#         'status': lambda i, _: i.status,
#         'type': lambda i, _: i.iteration_type,
#         'started': lambda i, _: i.date_started,
#         'ended': date_ended_getter,
#     },
# )

# def job(name):
#     """Retrieves the Job with the given name, or None."""
#     return get_object(Job, name=name)
# 
# def task(class_, id):
#     """Retrieves the task of type class_ and with the given ID, or None."""
#     return get_object(class_, id=id)
# 
# def region(name):
#     """Retrieves the ResourceRegion with the given name, or None."""
#     return get_object(ResourceRegion, name=name)
# 
# def iteration(id):
#     """Retrieves the Iteration with the given ID, or None."""
#     return get_object(Iteration, id=id)
# 
# def nds(id):
#     """Retrieves the NorcDaemonStatus with the given ID, or None."""
#     return get_object(NorcDaemonStatus, id=id)
# 
# def jobs():
#     return Job.objects.all()
# 
# def ndss(since_date=None, status_filter='all'):
#     """Retrieve NorcDaemonStatuses.
#     
#     Gets all NDSs that have ended since the given date or are still
#     running and match the given status filter.
#     
#     """
#     nds_query = NorcDaemonStatus.objects.all()
#     if since_date != None:
#         # Exclude lte instead of filter gte to retain running daemons.
#         nds_query = nds_query.exclude(date_ended__lte=since_date)
#     if status_filter != 'all' and status_filter in DAEMON_STATUS_DICT:
#         include_statuses = DAEMON_STATUS_DICT[status_filter.lower()]
#         nds_query = nds_query.filter(status__in=include_statuses)
#     return nds_query
# 
# def iterations(jid):
#     return Iteration.objects.filter(job__id=jid)
# 
# def tasks_from_iter(iid):
#     return TaskRunStatus.objects.filter(iteration__id=iid)
# 
# def trss(nds, status_filter='all', since_date=None):
#     """A hack fix so we can get the statuses for the proper daemon type."""
#     status_filter = status_filter.lower()
#     if nds.get_daemon_type() == 'NORC':
#         task_statuses = nds.taskrunstatus_set.all()
#     else:
#         task_statuses = nds.sqstaskrunstatus_set.all()
#     status_filter = status_filter.lower()
#     TRS_CATS = TaskRunStatus.STATUS_CATEGORIES
#     if not since_date == None:
#         task_statuses = task_statuses.exclude(date_ended__lt=since_date)
#     if status_filter != 'all' and status_filter in TRS_CATS:
#         only_statuses = TRS_CATS[status_filter]
#         task_statuses = task_statuses.filter(status__in=only_statuses)
#     return task_statuses
# 
# DEPR
# def get_task_statuses(status_filter='all'):
#     if status_filter == 'all':
#         TaskRunStatus.objects.all()
#     else:
#         include_statuses = TASK_STATUS_DICT[status_filter.lower()]
#         return TaskRunStatus.objects.filter(status__in=include_statuses)

